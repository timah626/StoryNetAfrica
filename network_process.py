import time
from messages import Message, MessageType

def network_process(inbox, node_queues):
    nodes = {}  # node_id → last_heartbeat_time
    DEAD_TIMEOUT = 10

    print("[NETWORK] Virtual network online")

    while True:
        while not inbox.empty():
            msg = inbox.get()

            if msg.type == MessageType.REGISTER:
                nodes[msg.sender] = time.time()
                print(f"[NETWORK] Node {msg.sender} registered")

            elif msg.type == MessageType.HEARTBEAT:
                nodes[msg.sender] = time.time()

            elif msg.type == MessageType.FILE_CHUNK:
                if msg.recipient in node_queues:
                    node_queues[msg.recipient].put(msg)
                else:
                    print(f"[NETWORK] LOST CHUNK {msg.payload['chunk_id']} "
                          f"from {msg.sender} → {msg.recipient}")
                    node_queues[msg.sender].put(Message(
                        type=MessageType.CHUNK_LOSS_REPORT,
                        sender="network",
                        payload={"chunk_id": msg.payload["chunk_id"]}
                    ))

              

        # Clean up dead nodes
        now = time.time()
        dead = [nid for nid, t in nodes.items() if now - t > DEAD_TIMEOUT]
        for nid in dead:
            print(f"[NETWORK] Node {nid} declared DEAD")
            del nodes[nid]

        time.sleep(0.01)
