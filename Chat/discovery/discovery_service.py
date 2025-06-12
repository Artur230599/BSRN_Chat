import socket
import threading
import toml
import time
import sys
import errno

BROADCAST_PORT = 4000
BUFFER_SIZE = 1024

def is_port_in_use(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        s.close()
        return False
    except socket.error as e:
        return e.errno == errno.EADDRINUSE

class DiscoveryService:
    def __init__(self, config_path):
        self.peers = {}
        self.peers_lock = threading.Lock()
        self.running = True

        self.config = self.load_config(config_path)
        print("[DEBUG] Geladene Konfiguration:", self.config)

        try:
            self.handle = self.config["handle"]
            self.port = int(self.config["port"])
        except KeyError as e:
            print(f"[Fehler] Fehlender Eintrag in TOML-Datei: {e}")
            sys.exit(1)

        self.whois_port = self.config.get("whoisport", 0)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', BROADCAST_PORT))

    @staticmethod
    def load_config(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return toml.load(f)
        except Exception as e:
            print(f"[Fehler] Konfigurationsdatei konnte nicht geladen werden: {e}")
            return {}

    def listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                message = data.decode("utf-8").strip()
                print(f"[DISCOVERY] Empfangen: {message} von {addr}")
                self.handle_message(message, addr)
            except Exception as e:
                print(f"[Fehler beim Empfangen] {e}")

    def handle_message(self, message, addr):
        parts = message.split()
        if not parts:
            return

        cmd = parts[0]

        if cmd == "JOIN" and len(parts) == 3:
            handle = parts[1]
            try:
                port = int(parts[2])
                with self.peers_lock:
                    self.peers[handle] = (addr[0], port)
            except ValueError:
                print("[Fehler] Ungültiger Port in JOIN.")

        elif cmd == "LEAVE" and len(parts) == 2:
            handle = parts[1]
            with self.peers_lock:
                self.peers.pop(handle, None)

        elif cmd == "WHOIS" and len(parts) == 2:
            target_handle = parts[1]
            if target_handle == self.handle:
                self.send_iam(addr)

        elif cmd == "IAM" and len(parts) == 4:
            handle = parts[1]
            ip = parts[2]
            try:
                port = int(parts[3])
                with self.peers_lock:
                    self.peers[handle] = (ip, port)
            except ValueError:
                print("[Fehler] Ungültiger Port in IAM.")

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
        except Exception:
            return "127.0.0.1"

    def send_join(self):
        msg = f"JOIN {self.handle} {self.port}\n"
        self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

    def send_leave(self):
        msg = f"LEAVE {self.handle}\n"
        self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

    def get_peers(self):
        with self.peers_lock:
            return dict(self.peers)

    def start(self):
        self.send_join()
        listener = threading.Thread(target=self.listen)
        listener.daemon = True
        listener.start()

    def stop(self):
        self.send_leave()
        self.running = False
        self.sock.close()

if __name__ == "__main__":
    if is_port_in_use(BROADCAST_PORT):
        print("[Abbruch] Discovery-Service läuft bereits (Port belegt).")
        sys.exit(1)

    service = DiscoveryService("slcp_config.toml")
    service.start()

    print("Discovery-Service läuft. Drücke Strg+C zum Beenden.")
    try:
        while True:
            time.sleep(1)
            peers = service.get_peers()
            print("Aktuelle Peers:", peers)
    except KeyboardInterrupt:
        print("Beende Discovery-Service...")
        service.stop()
