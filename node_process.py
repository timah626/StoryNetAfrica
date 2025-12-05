# node_process.py ← FINAL FIXED VERSION (works with usernames + listing)
import time
import os
from multiprocessing import Queue
from messages import Message, MessageType

CHUNK_SIZE = 1024 * 1024  # 1MB chunks (not used directly here but kept for consistency)

def create_folders(node_id):
    os.makedirs(f"nodes/{node_id}/inbox", exist_ok=True)
    os.makedirs(f"nodes/{node_id}/storage", exist_ok=True)
    os.makedirs(f"nodes/{node_id}/logs", exist_ok=True)

def node_process(node_id: str, network_queue: Queue, my_queue: Queue):
    create_folders(node_id)
    print(f"[NODE {node_id}] Starting up... PID: {os.getpid()}")

    # Register with scheduler
    network_queue.put(Message(type=MessageType.REGISTER, sender=node_id))

    last_heartbeat = 0
    active_transfers = {}

    while True:
        now = time.time()

        # Send heartbeat every 3 seconds
        if now - last_heartbeat > 3:
            network_queue.put(Message(type=MessageType.HEARTBEAT, sender=node_id))
            last_heartbeat = now

        # Process incoming messages
        while not my_queue.empty():
            msg = my_queue.get()

            if msg.type == MessageType.FILE_CHUNK:
                t_id = msg.transfer_id
                fname = msg.payload['file_name']
                chunk_id = msg.payload['chunk_id']
                total_chunks = msg.payload['total_chunks']
                data = msg.payload['data']
                username = msg.payload.get('username', 'unknown_user')  # ← CRUCIAL

                # Initialize transfer tracking
                if t_id not in active_transfers:
                    active_transfers[t_id] = {
                        "file_name": fname,
                        "total_chunks": total_chunks,
                        "received": set(),
                        "username": username
                    }

                # Save chunk to inbox
                inbox_path = f"nodes/{node_id}/inbox/{t_id}_{chunk_id}"
                with open(inbox_path, "wb") as f:
                    f.write(data)

                active_transfers[t_id]["received"].add(chunk_id)

                # When all chunks arrive → assemble file in user's folder
                if len(active_transfers[t_id]["received"]) == total_chunks:
                    user_dir = os.path.join("nodes", node_id, "storage", username)
                    os.makedirs(user_dir, exist_ok=True)
                    final_path = os.path.join(user_dir, fname)

                    with open(final_path, "wb") as outfile:
                        for i in range(total_chunks):
                            chunk_path = f"nodes/{node_id}/inbox/{t_id}_{i}"
                            if os.path.exists(chunk_path):
                                with open(chunk_path, "rb") as cf:
                                    outfile.write(cf.read())
                                os.remove(chunk_path)

                    print(f"[NODE {node_id}] File saved: {final_path} (user: {username})")
                    del active_transfers[t_id]

            elif msg.type == MessageType.TRANSFER_COMPLETE:
                print(f"[NODE {node_id}] Transfer complete: {msg.payload.get('file_name', 'unknown')}")

        time.sleep(0.05)






'''import time
import os
from multiprocessing import Queue
from messages import Message, MessageType

CHUNK_SIZE = 1024 * 1024

def create_folders(node_id):
    os.makedirs(f"nodes/{node_id}/inbox", exist_ok=True)
    os.makedirs(f"nodes/{node_id}/storage", exist_ok=True)
    os.makedirs(f"nodes/{node_id}/logs", exist_ok=True)

def node_process(node_id: str, network_queue: Queue, my_queue: Queue):
    create_folders(node_id)
    print(f"[NODE {node_id}] Starting up... PID: {os.getpid()}")

    network_queue.put(Message(type=MessageType.REGISTER, sender=node_id))

    last_heartbeat = 0
    active_transfers = {}

    while True:
        now = time.time()
        if now - last_heartbeat > 3:
            network_queue.put(Message(type=MessageType.HEARTBEAT, sender=node_id))
            last_heartbeat = now

        while not my_queue.empty():
            msg = my_queue.get()

            if msg.type == MessageType.FILE_CHUNK:
                t_id = msg.transfer_id
                fname = msg.payload['file_name']
                chunk_id = msg.payload['chunk_id']
                total_chunks = msg.payload['total_chunks']
                data = msg.payload['data']
                username = msg.payload.get('username', '')

                if t_id not in active_transfers:
                    active_transfers[t_id] = {
                        "file_name": fname,
                        "total_chunks": total_chunks,
                        "received": set(),
                        "username": username
                    }

                inbox_path = f"nodes/{node_id}/inbox/{t_id}_{chunk_id}"
                with open(inbox_path, "wb") as f:
                    f.write(data)

                active_transfers[t_id]["received"].add(chunk_id)

                if len(active_transfers[t_id]["received"]) == total_chunks:
                    user_dir = os.path.join("nodes", node_id, "storage", username)
                    os.makedirs(user_dir, exist_ok=True)
                    final_path = os.path.join(user_dir, fname)
                    with open(final_path, "wb") as outfile:
                        for i in range(total_chunks):
                            chunk_path = f"nodes/{node_id}/inbox/{t_id}_{i}"
                            with open(chunk_path, "rb") as cf:
                                outfile.write(cf.read())
                            os.remove(chunk_path)
                    print(f"[NODE {node_id}] File saved: {final_path}")
                    del active_transfers[t_id]

            elif msg.type == MessageType.TRANSFER_COMPLETE:
                print(f"[NODE {node_id}] Transfer complete: {msg.payload['file_name']}")

        time.sleep(0.05)'''













