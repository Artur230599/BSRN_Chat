import socket
import threading
import toml
import time
BROADCAST_PORT = 4000
BUFFER_SIZE = 1024
class DiscoveryService:
    def __init__(self, config_path):
        self.peers = {}  # {handle: (ip, port)}
        self.running = True
        self.config = self.load_config(config_path)
        self.handle = self.config["handle"]
        self.port = self.config["port"]
        self.whois_port = self.config["whoisport"]

        # UDP Socket für Broadcast
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', BROADCAST_PORT))

    def load_config(self, path):
        with open(path, "r") as f:
            return toml.load(f)

    def listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                message = data.decode("utf-8").strip()
                print(f"[DISCOVERY] Empfangen: {message} von {addr}")
                self.handle_message(message, addr)
            except Exception as e:
                print(f"[Fehler] {e}")

    def handle_message(self, message, addr):
        parts = message.split()
        if not parts:
            return
        cmd = parts[0]

        if cmd == "JOIN" and len(parts) == 3:
            handle, port = parts[1], int(parts[2])
            self.peers[handle] = (addr[0], port)
        elif cmd == "LEAVE" and len(parts) == 2:
            handle = parts[1]
            if handle in self.peers:
                del self.peers[handle]
        elif cmd == "WHOIS" and len(parts) == 2:
            if parts[1] == self.handle:
                self.send_iam(addr)
        elif cmd == "IAM" and len(parts) == 4:
            handle, ip, port = parts[1], parts[2], int(parts[3])
            self.peers[handle] = (ip, port)

    def send_iam(self, target_addr):
        msg = f"IAM {self.handle} {self.get_local_ip()} {self.port}\n"
        self.sock.sendto(msg.encode('utf-8'), target_addr)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def send_join(self):
        msg = f"JOIN {self.handle} {self.port}\n"
        self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

    def send_leave(self):
        msg = f"LEAVE {self.handle}\n"
        self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

    def start(self):
        self.send_join()
        listener = threading.Thread(target=self.listen)
        listener.daemon = True
        listener.start()

    def stop(self):
        self.send_leave()
        self.running = False
        self.sock.close()