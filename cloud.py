# cloud.py - FINAL WORKING VERSION
import bcrypt
import grpc
from concurrent import futures
import cloudsecurity_pb2
import cloudsecurity_pb2_grpc
from utils import send_otp, verify_otp, active_otps
import json
import os
import random
import tempfile

QUOTA_FILE = "user_quotas.json"
DEFAULT_QUOTA = 5 * 1024 * 1024 * 1024  # 5 GB
REPLICATION_FACTOR = 2

class UserServiceServicer(cloudsecurity_pb2_grpc.UserServiceServicer):
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.credentials = {}
        self.emails = {}
        self.quotas = {}
        self.load_credentials()
        self.load_quotas()

    def load_credentials(self):
        try:
            with open('credentials', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        username, email, hashed = line.split(',', 2)
                        self.credentials[username] = hashed
                        self.emails[username] = email
        except FileNotFoundError:
            open('credentials', 'w').close()

    def load_quotas(self):
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, 'r') as f:
                self.quotas = json.load(f)
        else:
            self.quotas = {}

    def save_quotas(self):
        with open(QUOTA_FILE, 'w') as f:
            json.dump(self.quotas, f, indent=2)

    def get_used_quota(self, username):
        return self.quotas.get(username, 0)

    def login(self, request, context):
        username = request.login
        password = request.password
        print(f"[SERVER] Login attempt: {username}")
        stored_hash = self.credentials.get(username)
        if not stored_hash or not bcrypt.checkpw(password.encode(), stored_hash.encode()):
            return cloudsecurity_pb2.Response(result="Unauthorized")
        if send_otp(self.emails[username], username):
            return cloudsecurity_pb2.Response(result="OTP_SENT")
        return cloudsecurity_pb2.Response(result="Email failed")

    def verifyOtp(self, request, context):
        username = request.login
        otp = request.password
        if verify_otp(username, otp):
            used = self.get_used_quota(username)
            free = DEFAULT_QUOTA - used
            gb_used = used // (1024*1024*1024)
            gb_free = free // (1024*1024*1024)
            print(f"[QUOTA] {username}: {gb_used} GB used | {gb_free} GB free")
            return cloudsecurity_pb2.Response(result="AUTH_SUCCESS")
        return cloudsecurity_pb2.Response(result="Invalid or expired OTP")

    def register(self, request, context):
        username = request.username.strip()
        email = request.email.strip().lower()
        password = request.password
        if username in self.credentials:
            return cloudsecurity_pb2.Response(result="Username already exists")
        if len(password) < 6:
            return cloudsecurity_pb2.Response(result="Password too short")
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with open('credentials', 'a') as f:
            f.write(f"{username},{email},{hashed}\n")
        self.credentials[username] = hashed
        self.emails[username] = email
        if username not in self.quotas:
            self.quotas[username] = 0
            self.save_quotas()
        return cloudsecurity_pb2.Response(result="Registration successful! You can now login.")

    def upload(self, request, context):
        username = request.username
        filename = request.filename
        data = request.data
        size = len(data)

        used = self.get_used_quota(username)
        if used + size > DEFAULT_QUOTA:
            free_mb = (DEFAULT_QUOTA - used) / (1024 * 1024)
            return cloudsecurity_pb2.Response(
                result=f"Not enough storage! You only have {free_mb:.4f} MB free (5 GB total limit)"
            )

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        all_nodes = list(self.scheduler.node_outboxes.keys())
        if len(all_nodes) < REPLICATION_FACTOR:
            os.unlink(tmp_path)
            return cloudsecurity_pb2.Response(result="Not enough nodes online! Need at least 2.")

        chosen = random.sample(all_nodes, REPLICATION_FACTOR)
        
        for node in chosen:
            self.scheduler.send_file(tmp_path, "controller", node, username=username, original_name=filename)

        os.unlink(tmp_path)

        self.quotas[username] = used + size
        self.save_quotas()

        return cloudsecurity_pb2.Response(
            result=f"Uploaded '{filename}' → replicated on {', '.join(chosen)}"
        )

    def listFiles(self, request, context):
        username = request.username
        print(f"[LISTFILES] Called for user: {username}")
        
        files = []
        sizes = []
        seen = set()

        nodes_dir = "nodes"
        
        if not os.path.exists(nodes_dir):
            print(f"[LISTFILES] No nodes directory found")
            return cloudsecurity_pb2.FileList(filenames=[], sizes=[])

        print(f"[LISTFILES] Found nodes directory")

        try:
            for node in os.listdir(nodes_dir):
                node_path = os.path.join(nodes_dir, node, "storage", username)
                
                if os.path.isdir(node_path):
                    print(f"[LISTFILES] Checking node: {node}")
                    
                    for f in os.listdir(node_path):
                        if f not in seen:
                            seen.add(f)
                            file_path = os.path.join(node_path, f)
                            
                            try:
                                size = os.path.getsize(file_path)
                                print(f"[LISTFILES] Added: {f} ({size} bytes)")
                                files.append(f)
                                sizes.append(size)
                            except Exception as e:
                                print(f"[LISTFILES] Error getting size: {e}")
                                files.append(f)
                                sizes.append(0)
        
        except Exception as e:
            print(f"[LISTFILES] Error: {e}")
            import traceback
            traceback.print_exc()

        print(f"[LISTFILES] Returning {len(files)} files")
        return cloudsecurity_pb2.FileList(filenames=files, sizes=sizes)

    def download(self, request, context):
        username = request.username
        filename = request.filename
        for node in list(self.scheduler.node_outboxes.keys()):
            path = os.path.join("nodes", node, "storage", username, filename)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    return cloudsecurity_pb2.DownloadResponse(success=True, data=f.read())
        return cloudsecurity_pb2.DownloadResponse(success=False, result="File not found")

    def deleteFile(self, request, context):
        username = request.username
        filename = request.filename

        deleted_from = []
        freed_space = 0

        for node in list(self.scheduler.node_outboxes.keys()):
            user_dir = os.path.join("nodes", node, "storage", username)
            file_path = os.path.join(user_dir, filename)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                os.remove(file_path)
                deleted_from.append(node)
                freed_space += size

        if deleted_from:
            if username in self.quotas:
                self.quotas[username] -= freed_space
                if self.quotas[username] < 0:
                    self.quotas[username] = 0
                self.save_quotas()

            return cloudsecurity_pb2.Response(
                result=f"Deleted '{filename}' from {', '.join(deleted_from)} | {freed_space/(1024*1024):.2f} MB freed!"
            )
        else:
            return cloudsecurity_pb2.Response(result="File not found")


def serve(scheduler=None):
    if scheduler is None:
        from scheduler import CloudScheduler
        import multiprocessing as mp
        scheduler = CloudScheduler(mp.Queue(), {})

    MAX_MESSAGE_SIZE = 1024 * 1024 * 1024  # 1 GB

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', MAX_MESSAGE_SIZE),
            ('grpc.max_receive_message_length', MAX_MESSAGE_SIZE)
        ]
    )

    cloudsecurity_pb2_grpc.add_UserServiceServicer_to_server(UserServiceServicer(scheduler), server)
    server.add_insecure_port('[::]:51234')
    print('Starting Auth + File Server...', end='')
    server.start()
    print(' [OK]')
    server.wait_for_termination()


if __name__ == '__main__':
    serve()