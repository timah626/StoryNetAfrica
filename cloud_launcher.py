# cloud_launcher.py  ←  FINAL WITH UPLOAD/DOWNLOAD MENU + REAL NODES
import multiprocessing as mp
import threading
import time
import os
import sys
import grpc
import cloudsecurity_pb2
import cloudsecurity_pb2_grpc
from cloud import serve, UserServiceServicer
from scheduler import CloudScheduler
import node_process as node_mod
from messages import Message, MessageType

# === CONFIG ===
NODES = ["node 1", "node 2", "node 3"]
GRPC_PORT = 51234

# Global queues
network_queue = mp.Queue()
node_outboxes = {}

def start_nodes():
    procs = []
    for node_id in NODES:
        q = mp.Queue()
        node_outboxes[node_id] = q
        p = mp.Process(target=node_mod.node_process, args=(node_id, network_queue, q), daemon=True)
        p.start()
        procs.append(p)
        time.sleep(0.2)
    print(f"[LAUNCHER] All {len(NODES)} nodes started")
    return procs

def start_grpc_server():
    scheduler = CloudScheduler(network_queue, node_outboxes)
    threading.Thread(target=serve, args=(scheduler,), daemon=True).start()
    time.sleep(2)
    print("[LAUNCHER] gRPC server ready")

def upload_file(stub, username):
    path = input("Enter full file path: ").strip().strip('"')
    if not os.path.exists(path):
        print("File not found!")
        return
    with open(path, "rb") as f:
        data = f.read()
    resp = stub.upload(cloudsecurity_pb2.UploadRequest(
        username=username,
        filename=os.path.basename(path),
        data=data
    ))
    print(f"\n{resp.result}\n")

def list_files(stub, username):
    resp = stub.listFiles(cloudsecurity_pb2.UserRequest(username=username))
    print("\nYour files:")
    if not resp.filenames:
        print("  (empty)")
    for i, name in enumerate(resp.filenames):
        size_mb = resp.sizes[i] / (1024*1024)
        print(f"  • {name} ({size_mb:.2f} MB)")


def download_file(stub, username):
    filename = input("File to download: ").strip()
    resp = stub.download(cloudsecurity_pb2.DownloadRequest(username=username, filename=filename))
    if resp.success:
        os.makedirs("downloads", exist_ok=True)
        save_path = os.path.join("downloads", filename)
        with open(save_path, "wb") as f:
            f.write(resp.data)
        print(f"Downloaded → {save_path}")
    else:
        print("File not found")

def delete_file(stub, username):
    filename = input("File to delete: ").strip()
    if not filename:
        return
    resp = stub.deleteFile(cloudsecurity_pb2.DeleteRequest(username=username, filename=filename))
    print(f"\n{resp.result}\n")
    input("Press Enter to continue...")





def login_and_enter_console(stub):
    print("\n=== LOGIN ===")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    resp = stub.login(cloudsecurity_pb2.Request(login=username, password=password))
    print(f"→ {resp.result}")

    if "OTP_SENT" not in resp.result:
        return None

    otp = input("Enter OTP: ").strip()
    resp2 = stub.verifyOtp(cloudsecurity_pb2.Request(login=username, password=otp))

    if resp2.result == "AUTH_SUCCESS":
        print("\nACCESS GRANTED! Welcome.")
        return username
    return None

def main():
    print("=== CLOUD SIMULATOR – SECURED WITH 2FA + REAL NODES ===\n")
    
    # Start everything
    start_nodes()
    start_grpc_server()

    channel = grpc.insecure_channel(f'localhost:{GRPC_PORT}')
    stub = cloudsecurity_pb2_grpc.UserServiceStub(channel)

    username = login_and_enter_console(stub)
    if not username:
        print("Login failed. Bye.")
        return

    while True:
        print(f"\nLogged in as: {username}")
        print("[1] Upload file")
        print("[2] List my files")
        print("[3] Download file")
        print("[4] Delete file")
        print("[4] Logout")
        choice = input("\nChoose: ").strip()

        if choice == "1":
            upload_file(stub, username)
        elif choice == "2":
            list_files(stub, username)
        elif choice == "3":
            download_file(stub, username)
        elif choice == "4":
            delete_file(stub, username)
        elif choice == "5":
            print("Bye!")
            break

if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    main()