import socket
import time
import threading
from typing import List
import enum
import random

from matplotlib.pyplot import connect
from nodeconnection import NodeConnection

class State(enum.Enum):
    F = 1
    NF = 2

class Node(threading.Thread):

    def __init__(self, port: int, id: int):

        super(Node, self).__init__(daemon=True)
        self.terminate_flag = threading.Event()

        self.host = "127.0.0.1" #Allow only localhost
        self.port: int = port

        self.state = State.NF
        self.role = "secondary"

        self.queue = []

        self.timestamp: int = 0
        self.message_timestamp: int = -1
        self.callback = self.node_callback

        self.connections: List[NodeConnection] = [] 

        self.id: int = id

        # Start the TCP/IP server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.init_server()


    def node_callback(self, data: dict):
        command: str = data.get("command")
        #print(f"[P{self.id}] Got command with data {data}")
        if command == "g-state":
            print(f"G{self.id}, {self.role}, state={self.state.name}")
        if command == "attack":
            return
        if command == "retreat":
            return
        elif command == "exit":
            self.stop()

    def init_server(self):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(None)
        self.sock.listen(1)

    def send_to_nodes(self, data: dict):
        for connection in self.connections:
            connection.send(data)

    def send_to_self(self, data: dict):
        self.node_callback(data)

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

    def create_new_connection(self, sock, id: int, port: int):
        return NodeConnection(self, sock, int(id), port)

    def create_ok_payload(self):
        return {"command": "ok", "id": self.id, "timestamp": self.timestamp}

    def run(self):
        while not self.terminate_flag.is_set():
            try:
                connection, client_address = self.sock.accept()

                connected_node_id = connection.recv(4096).decode('utf-8')
                connection.send(str(self.id).encode('utf-8'))

                thread_client = self.create_new_connection(connection, connected_node_id, client_address[1])
                thread_client.start()
            
            except Exception as e:
                raise e

            time.sleep(0.01)

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