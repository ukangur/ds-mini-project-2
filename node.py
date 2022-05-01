import socket
import time
import threading
from typing import List
import enum

from matplotlib.pyplot import connect
from nodeconnection import NodeConnection

class State(enum.Enum):
    F = 1
    NF = 2

class Role(enum.Enum):
    PRIMARY = 1,
    SECONDARY = 2

class Node(threading.Thread):

    def __init__(self, port: int, id: int, is_primary: bool):

        super(Node, self).__init__(daemon=True)
        self.terminate_flag = threading.Event()

        self.id: int = id
        self.host = "127.0.0.1" #Allow only localhost
        self.port: int = port

        self.state = State.NF
        self.role = Role.PRIMARY if is_primary else Role.SECONDARY
        self.callback = self.node_callback

        self.connections: List[NodeConnection] = [] 


        # Start the TCP/IP server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_server()


    def node_callback(self, data: dict):
        command: str = data.get("command")
        #print(f"[G{self.id}] Got command with data {data}")
        if command == "g-state":
            state = data.get("state")
            if state is None:
                print(f"G{self.id}, {self.role.name.lower()}, state={self.state.name}")
            else:
                self.state = State.F if state == "faulty" else State.NF
        elif command == "g-kill":
            id = data.get("id")
            if self.id == id:
                self.stop()
            else:
                for conn in self.connections:
                    if conn.id == id:
                        conn.stop()
        elif command == "actual-order":
            return
        elif command == "set-primary":
            self.role = Role.PRIMARY
        elif command == "simple-state":
            print(f"G{self.id}, {self.role.name.lower()}")

    def init_server(self):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(None)
        self.sock.listen(1)

    def send_to_nodes(self, data: dict):
        for connection in self.connections:
            connection.send(data)

    def send_to_self(self, data: dict):
        self.send_to_node_with_id(data, self.id)

    def send_to_node_with_id(self, data: dict, id: int):
        for connection in self.connections:
            if connection.id == id:
                connection.send(data)
                break

    def connect_with_node(self, port: int):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, port))

            sock.send(str(self.id).encode('utf-8'))
            connected_node_id = sock.recv(4096).decode('utf-8')

            thread_client = self.create_new_connection(sock, connected_node_id, port)
            thread_client.start()

            self.connections.append(thread_client)
            return True

        except:
            return False

    def stop(self):
        self.terminate_flag.set()
        self.connect_with_node(self.port)

    def create_new_connection(self, sock, id: int, port: int):
        return NodeConnection(self, sock, int(id), port)

    def create_ok_payload(self):
        return {"command": "ok", "id": self.id, "timestamp": self.timestamp}

    def run(self):
        while not self.terminate_flag.is_set():
            connection, client_address = self.sock.accept()
            connected_node_id = connection.recv(4096).decode('utf-8')
            connection.send(str(self.id).encode('utf-8'))

            thread_client = self.create_new_connection(connection, connected_node_id, client_address[1])
            thread_client.start()
            time.sleep(0.01)

        print(f"G{self.id} - Shutting down")
        for t in self.connections:
            t.send(str("STOP").encode("utf-8"))
        for t in self.connections:
            t.stop()
        time.sleep(1)

        for t in self.connections:
            t.join()

        self.sock.settimeout(None)   
        self.sock.close()

    def node_message(self, data):
        if self.callback is not None:
            self.callback(data)

    def __repr__(self) -> str:
        return f"Node(id: {self.id}, state: {self.state.name}, timestamp: {self.timestamp})"