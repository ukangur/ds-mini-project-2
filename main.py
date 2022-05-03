import sys
from typing import List
import node
import os
import random

START_PORT = 6394

LIST_PAYLOAD = {"command": "g-state"}
EXIT_PAYLOAD = {"command": "exit"}
ATTACK_PAYLOAD = {"command": "actual-order", "order": "attack"}
RETREAT_PAYLOAD = {"command": "actual-order", "order": "retreat"}
SET_PRIMARY_PAYLOAD = {"command": "set-primary"}
SIMPLE_STATE_PAYLOAD = {"command": "simple-state"}
ALLOWED_STATES = ["faulty", "non-faulty"]
COMMANDS = "g-state <ID> <state>, g-add <K>, g-kill <ID>, g-state, actual-order <ORDER>"

def start(num_threads: int) -> List[node.Node]:
    nodes: List[node.Node] = []
    primary_index = random.randint(0, num_threads - 1)
    for i in range(num_threads):
        new_node = node.Node(START_PORT + i, i + 1, i == primary_index)
        nodes.append(new_node)
        new_node.start()
    for start_node in nodes:
        for end_node in nodes:
            if start_node.id != end_node.id:
                start_node.connect_with_node(end_node.port)
    return nodes

def start_new_nodes(nodes: List[node.Node], k: int):
    max_id = max([n.id for n in nodes])
    new_nodes: List[node.Node] = []
    for i in range(k):
        new_node = node.Node(START_PORT + max_id + i, max_id + i + 1, False)
        new_nodes.append(new_node)
        new_node.start()
    for start_node in new_nodes:
        for end_node in nodes:
            if start_node.id != end_node.id:
                start_node.connect_with_node(end_node.port)
                end_node.connect_with_node(start_node.port)      
    nodes.extend(new_nodes)
    return nodes


def run(nodes: List[node.Node]):
    print(f"Commands: {COMMANDS}")
    command = None
    try:
        while command != 'exit':
            command = str(input("Enter command: ")).lower().rstrip()
            parts = command.split(" ")
            if parts[0] == "g-state":
                if(len(parts) > 1):
                    handle_change(nodes, parts)
                else:    
                    selfcast(nodes, LIST_PAYLOAD)
            elif parts[0] == "actual-order":
                handle_order(nodes, parts)
            elif parts[0] == "g-add":
                nodes = handle_add(nodes, parts)
                handle_simple_state(nodes)
            elif parts[0] == "g-kill":
                nodes = handle_kill(nodes, parts)
                handle_simple_state(nodes)
            elif parts[0] == "exit":
                stop_nodes(nodes)
                os._exit(0)
            else:
                print(f"{parts[0]} is not a valid command")
                print(f"Commands: {COMMANDS}")

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

def handle_order(nodes: List[node.Node], parts: List[str]):
    if len(parts) == 2:
        faultynodecount : int = count_faulty_nodes(nodes)
        if (3 * faultynodecount + 1) > len(nodes):
            print(f"Execute order: cannot be determined – not enough generals in the system! {faultynodecount} faulty node in the system - {len(nodes)-1} out of {len(nodes)} quorum not consistent")
            return
        _, order = parts
        primary_node = get_primary_node(nodes)
        primary_node_id = primary_node.id
        if order == "attack":
                data = {"command": "actual-order", "order": "attack", "primary_id": primary_node_id, "faulty_count":faultynodecount}
                primary_node.send_to_self(data)
        elif order == "retreat":
                data = {"command": "actual-order", "order": "retreat", "primary_id": primary_node_id, "faulty_count":faultynodecount}
                primary_node.send_to_self(data)
        else:
            print(f"Expected an attack or retreat order, got {order}")

    else:
        print(f"Expected only order parameter")

def handle_kill(nodes: List[node.Node], parts: List[str]):
    if len(parts) == 2:
        command, id = parts
        try:
                if check_id(nodes,int(id)):
                    data = {"command": command, "id" : int(id)}
                    primary_node = get_primary_node(nodes)
                    primary_node.send_to_nodes(data)
                    primary_node.send_to_self(data)
                    new_nodes = [n for n in nodes if n.id != int(id)]
                    if primary_node.id == int(id):
                        new_primary_id = random.choice([n.id for n in new_nodes])
                        primary_node.send_to_node_with_id(SET_PRIMARY_PAYLOAD, new_primary_id)
                    return new_nodes
                else:
                    print(f"No node with id {id}")
                    return nodes
        except ValueError:
            print(f"Expected a valid integer, got {id}")
            return nodes
    else:
        print(f"Expected only id parameter")
        return nodes


def handle_add(nodes: List[node.Node], parts: List[str]):
    if len(parts) == 2:
        try:
            _, k = parts
            return start_new_nodes(nodes, int(k))
        except ValueError:
            print(f"Expected a valid integer, got {k}")
    else:
        print(f"Expected only number of new nodes")

def handle_change(nodes: List[node.Node], parts: List[str]):
    if len(parts) == 3:
        command, id, state = parts
        if state.lower() not in ALLOWED_STATES:
            print(f"Incorrect state - expected one of {ALLOWED_STATES}")
        try:
            data = {"command": command, "state": state.lower()}
            get_primary_node(nodes).send_to_node_with_id(data, int(id))
        except ValueError:
            print(f"Expected a valid integer, got {id}")
    else:
        print(f"Expected id and state parameter")

def handle_simple_state(nodes: List[node.Node]):
    for n in nodes:
        n.send_to_self(SIMPLE_STATE_PAYLOAD)

def get_primary_node(nodes: List[node.Node]):
    for n in nodes:
        if n.role == node.Role.PRIMARY:
            return n
    raise Exception("Did not find primary node")

def count_faulty_nodes(nodes: List[node.Node]):
    counter = 0
    for n in nodes:
        if n.state == node.State.F:
            counter += 1
    return counter

def check_id(nodes: List[node.Node], id: int):
    for node in nodes:
        if node.id == id:
            return True
    
    return False

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