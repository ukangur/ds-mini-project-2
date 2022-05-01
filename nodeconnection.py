import time
import threading
import json
import socket

class NodeConnection(threading.Thread):
    def __init__(self, main_node, sock: socket.socket, id: int, port: int):

        super(NodeConnection, self).__init__()
        self.host = "127.0.0.1"
        self.port = port
        self.main_node = main_node
        self.sock = sock
        self.terminate_flag = threading.Event()

        self.id = id
        self.EOT_CHAR = 0x04.to_bytes(1, 'big')

    def send(self, data):
        try:
            json_data = json.dumps(data)
            json_data = json_data.encode('utf-8') + self.EOT_CHAR
            self.sock.sendall(json_data)
        except:
            self.stop() # Stopping node due to failure

    def stop(self):
        self.terminate_flag.set()

    def parse_packet(self, packet: bytes):
        try:
            packet_decoded = packet.decode('utf-8')

            try:
                return json.loads(packet_decoded)

            except json.decoder.JSONDecodeError:
                return packet_decoded

        except UnicodeDecodeError:
            return packet

    def run(self):         
        buffer = b''
        while not self.terminate_flag.is_set():
            chunk = b''
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                chunk = b''
            if chunk != b'':
                buffer += chunk
                eot_pos = buffer.find(self.EOT_CHAR)

                while eot_pos > 0:
                    packet = buffer[:eot_pos]
                    buffer = buffer[eot_pos + 1:]
                    self.main_node.node_message(self.parse_packet(packet))

                    eot_pos = buffer.find(self.EOT_CHAR)
                time.sleep(0.01)
        self.sock.settimeout(None)
        self.sock.close()