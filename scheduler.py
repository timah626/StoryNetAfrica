# scheduler.py ← FINAL WORKING VERSION WITH ROUTING LOOP
# scheduler.py ← 100% FINAL WORKING VERSION
import os
import time
import hashlib
import random
import threading
from messages import Message, MessageType

MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1 GB limit


class CloudScheduler:
    def __init__(self, network_queue, node_outboxes):
        self.network_queue = network_queue
        self.node_outboxes = node_outboxes
        self.active_nodes = set()

        # Start background router
        threading.Thread(target=self._route_messages, daemon=True).start()

    def _route_messages(self):
        print("[SCHEDULER] Message router started")
        while True:
            try:
                msg = self.network_queue.get(timeout=1)
                if msg.type == MessageType.REGISTER:
                    self.active_nodes.add(msg.sender)
                    print(f"[SCHEDULER] Node registered: {msg.sender}")
                elif msg.type == MessageType.HEARTBEAT:
                    self.active_nodes.add(msg.sender)
                elif msg.recipient and msg.recipient in self.node_outboxes:
                    self.node_outboxes[msg.recipient].put(msg)
            except:
                pass  # queue empty

    def send_file(self, file_path: str, source_node: str, target_node: str, username: str = None, original_name: str = None):
        if not os.path.exists(file_path):
            print(f"[SCHEDULER] File {file_path} not found!")
            return False

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            print("[SCHEDULER] File too big (>10MB)")
            return False

        file_name = original_name if original_name else os.path.basename(file_path)
        transfer_id = hashlib.md5(f"{file_name}{time.time()}{random.randint(0,99999)}".encode()).hexdigest()[:12]

        with open(file_path, "rb") as f:
            data = f.read()

        chunk_size = 1024 * 1024
        total_chunks = (len(data) + chunk_size - 1) // chunk_size

        print(f"[SCHEDULER] Replicating '{file_name}' → {target_node} (user: {username})")

        for i in range(total_chunks):
            chunk_data = data[i * chunk_size:(i + 1) * chunk_size]
            payload = {
                'chunk_id': i,
                'data': chunk_data,
                'total_chunks': total_chunks,
                'file_name': file_name,
                'username': username
            }
            msg = Message(
                type=MessageType.FILE_CHUNK,
                sender=source_node,
                recipient=target_node,
                transfer_id=transfer_id,
                payload=payload
            )
            self.network_queue.put(msg)
            time.sleep(0.005)

        self.network_queue.put(Message(
            type=MessageType.TRANSFER_COMPLETE,
            sender=source_node,
            recipient=target_node,
            transfer_id=transfer_id,
            payload={"file_name": file_name}
        ))
        return True

    def get_active_nodes(self):
        return list(self.active_nodes)
