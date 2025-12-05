import multiprocessing as mp
import time
import os
from node_process import node_process
from network_process import network_process
from scheduler import CloudScheduler

def main():
    mp.set_start_method("spawn", force=True)
    print("\n=== CLOUD SIMULATION (Spawn + Auto-Restart + File Transfer) ===\n")

    manager = mp.Manager()
    network_queue = manager.Queue()
    node_queues = manager.dict()

    # Nodes to run
    nodes = ["node1", "node2", "node3"]
    for nid in nodes:
        node_queues[nid] = manager.Queue()

    # Start network
    net_proc = mp.Process(target=network_process, args=(network_queue, node_queues))
    net_proc.start()
    print("[MAIN] Network started\n")

    scheduler = CloudScheduler(network_queue, node_queues)

    # Start node processes
    processes = {}
    for nid in nodes:
        p = mp.Process(target=node_process, args=(nid, network_queue, node_queues[nid]))
        p.start()
        processes[nid] = p
        print(f"[MAIN] Started {nid}")

    # --- CREATE TEST FILES ---
    os.makedirs("files_to_send", exist_ok=True)
    test_files = [
        ("file_small.txt", 1_000_000, "A"),
        ("file_medium.txt", 5_000_000, "B"),
        ("file_large.txt", 9_000_000, "C"),
    ]
    for fname, size, char in test_files:
        path = os.path.join("files_to_send", fname)
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(char * size)
            print(f"[MAIN] Created {fname} ({size//1_000_000}MB)")

    time.sleep(2)  # wait for nodes to register

    # --- SEND FILES ---
    transfers = [
        ("file_small.txt", "node1", "node2"),
        ("file_medium.txt", "node1", "node3"),
        ("file_large.txt", "node2", "node1")
    ]
    for file_path, src, dst in transfers:
        print(f"\n[MAIN] Scheduling transfer: {file_path} {src} → {dst}")
        scheduler.send_file(os.path.join("files_to_send", file_path), src, dst)
        time.sleep(1)

    # --- MONITOR & AUTO-RESTART NODES ---
    try:
        while True:
            time.sleep(2)
            for nid, proc in processes.items():
                if not proc.is_alive():
                    print(f"[MAIN] Node {nid} DEAD → restarting...")
                    new_p = mp.Process(target=node_process, args=(nid, network_queue, node_queues[nid]))
                    new_p.start()
                    processes[nid] = new_p
                    print(f"[MAIN] Node {nid} restarted")
    except KeyboardInterrupt:
        print("\n[MAIN] Shutting down...")
        net_proc.terminate()
        for p in processes.values():
            p.terminate()
        print("[MAIN] Bye.")

if __name__ == "__main__":
    main()
