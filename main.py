import sys
from typing import List
import node
import os

START_PORT = 6394

LIST_PAYLOAD = {"command": "g-state"}
ATTACK_PAYLOAD = {"command": "attack"}
RETREAT_PAYLOAD = {"command": "retreat"}
EXIT_PAYLOAD = {"command": "exit"}

def start(num_threads: int) -> List[node.Node]:
    nodes: List[node.Node] = []
    for i in range(num_threads):
        new_node = node.Node(START_PORT + i, i + 1)
        nodes.append(new_node)
        new_node.start()
    for start_node in nodes:
        for end_node in nodes:
            if start_node.id != end_node.id:
                start_node.connect_with_node(end_node.port)
    return nodes

def run(nodes: List[node.Node]):
    print("Commands: ...")
    command = None
    try:
        while command != 'exit':
            command = str(input("Enter command: ")).lower().rstrip()
            parts = command.split(" ")
            if parts[0] == "g-state":
                selfcast(nodes, LIST_PAYLOAD)
            elif parts[0] == "exit":
                stop_nodes(nodes)
                os._exit(0)
            else:
                print(f"{parts[0]} is not a valid command")
                print("Commands: ...")

    except KeyboardInterrupt:
        stop_nodes(nodes)
        os._exit(0)

def selfcast(nodes: List[node.Node], msg: dict):
    for node in nodes:
        node.send_to_self(msg)

def broadcast(nodes: List[node.Node], msg: dict):
    for node in nodes:
        node.send_to_nodes(msg)

def stop_nodes(nodes: List[node.Node]):
    selfcast(nodes, EXIT_PAYLOAD)


if __name__=='__main__':
    if len(sys.argv) < 2:
        exit(f"Usage {sys.argv[0]} NUM_THREADS")
    try:
        num_threads = int(sys.argv[1])
    except ValueError:
        exit(f"Expecting an integer as num_threads. Got {sys.argv[1]}")
    if num_threads <= 0:
        exit(f"The number of threads must be positive. Got {num_threads}")
    nodes = start(num_threads)
    run(nodes)