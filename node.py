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
        self.vote = None
        self.received_votes: List[bool] = []

        self.send_connections: List[NodeConnection] = [] 
        self.recv_connections: List[NodeConnection] = []

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
                index = -1
                for i, conn in enumerate(self.send_connections):
                    if conn.id == id:
                        conn.stop()
                        index = i
                        break
                self.send_connections.pop(index)
                index = -1
                for i, conn in enumerate(self.recv_connections):
                    if conn.id == id:
                        conn.stop()
                        index = i
                        break
                self.recv_connections.pop(index)

        elif command == "actual-order":
            faulty_node_count = data.get("faulty_count")
            order: str = data.get("order")
            primary_id: int = data.get("primary_id")
            if self.state == State.NF:
                data = {"command": "set-vote", "vote": True}
                print("Sending vote True to everyone")
                self.send_to_nodes(data)
                data = {"command": "get-order", "primary_id": primary_id}
            else:
                for node in self.send_connections:
                    data = {"command": "set-vote", "vote": bool(random.getrandbits(1))}
                    self.send_to_node_with_id(data,node)
                data = {"command": "get-order","primary_id": primary_id}
            time.sleep(0.5)
            self.send_to_nodes(data)
            while len(self.received_votes) < len(self.recv_connections):
                time.sleep(1)
            print(f"These are the votes - {self.received_votes}")

            decisions_true = self.received_votes.count(True)
            decisions_false = self.received_votes.count(False)

            if decisions_true > decisions_false:
                if(faulty_node_count == 0):
                    print(f"Execute order: {order}! Non-faulty nodes in the system - {decisions_true} out of {decisions_true+decisions_false+1} quorum suggest {order}")
                else:
                    print(f"Execute order: {order}! {faulty_node_count} faulty nodes in the system - {decisions_true} out of {decisions_true+decisions_false+1} quorum suggest {order}")
            else:
                if(faulty_node_count == 0):
                    print(f"Do not execute order: {order}! Non-faulty nodes in the system - {decisions_true} out of {decisions_true+decisions_false+1} quorum suggest not to {order}")
                else:
                    print(f"Do not execute order: {order}! {faulty_node_count} faulty in the system - {decisions_true} out of {decisions_true+decisions_false+1} quorum suggest not to {order}")

        elif command == "set-vote":
            vote: bool = data.get("vote")
            if(vote):
                self.vote = vote
            else:
                self.vote = bool(random.getrandbits(1))

        elif command == "get-order":
            print(f"Made it to counting votes for node {self.id}")
            primary_id = data.get("primary_id")
            vote: bool = data.get("vote")
            self.received_votes.append(self.vote)
            data = {"command": "get-votes", "sender_id": self.id}
            self.send_to_nodes_except_id(data,primary_id)
            while len(self.received_votes) < len(self.recv_connections):
                time.sleep(1)

            print(f"The vote list for node {self.id} is {self.received_votes}")
        
            votes_true = self.received_votes.count(True)
            votes_false = self.received_votes.count(False)

            if(votes_true > votes_false):
                data = {"command": "receive-vote", "vote": True}
            else:
                data = {"command": "receive-vote", "vote": False}

            self.send_to_node_with_id(data,primary_id)

        elif command == "get-votes":
            sender_id = data.get("sender_id")
            if self.state == State.NF:
                data = {"command": "receive-vote", "vote": self.vote}
            else:
                data = {"command": "receive-vote", "vote": bool(random.getrandbits(1))}
            self.send_to_node_with_id(data,sender_id)

        elif command == "receive-vote":
            vote = data.get("vote")
            self.received_votes.append(vote)

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
        for connection in self.send_connections:
            connection.send(data)

    def send_to_self(self, data: dict):
        self.node_callback(data)

    def send_to_node_with_id(self, data: dict, id: int):
        for connection in self.send_connections:
            if connection.id == id:
                connection.send(data)
                break

    def send_to_nodes_except_id(self, data: dict, id: int):
        for connection in self.send_connections:
            if connection.id != id:
                connection.send(data)
    

    def connect_with_node(self, port: int):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, port))

            sock.send(str(self.id).encode('utf-8'))
            connected_node_id = sock.recv(4096).decode('utf-8')

            #Sending NodeConnection
            thread_client = self.create_new_connection(sock, connected_node_id, port)
            thread_client.start()

            self.send_connections.append(thread_client)
            return True

        except:
            return False

    def stop(self):
        self.terminate_flag.set()
        self.connect_with_node(self.port)

    def create_new_connection(self, sock: socket.socket, id: int, port: int):
        return NodeConnection(self, sock, int(id), port)

    def run(self):
        while not self.terminate_flag.is_set():
            connection, client_address = self.sock.accept()
            connection.settimeout(1)
            connected_node_id = connection.recv(4096).decode('utf-8')
            connection.send(str(self.id).encode('utf-8'))

            #Receiving NodeConnection
            thread_client = self.create_new_connection(connection, connected_node_id, client_address[1])
            thread_client.start()
            self.recv_connections.append(thread_client)
            time.sleep(0.01)

        for t in self.send_connections:
            t.stop()
        for t in self.recv_connections:
            t.stop()

        time.sleep(1)
        for t in self.send_connections:
            t.join()
        for t in self.recv_connections:
            t.join()

        self.sock.settimeout(None)   
        self.sock.close()

    def node_message(self, data):
        if self.callback is not None:
            self.callback(data)

    def __repr__(self) -> str:
        return f"Node(id: {self.id}, state: {self.state.name}, timestamp: {self.timestamp})"