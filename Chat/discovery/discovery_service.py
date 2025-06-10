import socket
import threading
import toml
import time
import sys
import errno

BROADCAST_PORT = 4000
BUFFER_SIZE = 1024
def is_port_in_use(port: object) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((" ", port))
        s.close()
        return False
    except socket.error as e:
        return e.errno == errno.EADDRINUSE



##
# @class DiscoveryService
# @brief diese Klasse ermöglicht das Finden (Discovery) von Peers über UDP-Broadcast im lokalen Netzwerk.
class DiscoveryService:
    ##
    # @brief Konstruktor : Initialisiert das DiscoveryService-Objekt.
    # @param config_path Der Pfad zur Konfigurationsdatei (.toml)
    def __init__(self, config_path):
        self.peers = {}  # {handle: (ip, port)}
        self.peers_lock = threading.Lock()
        self.running = True
        self.config = self.load_config(config_path)
        self.handle = self.config["handle"]
        self.port = self.config["port"]
        self.whois_port = self.config["wohlsport"]

        # UDP Socket für Broadcast
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', BROADCAST_PORT))

    ##
    # @brief Lädt die Konfiguration aus einer TOML-Datei.
    # @param path Der Pfad zur Konfigurationsdatei.
    # @return Gibt die Konfiguration als Dictionary zurück.
    @staticmethod
    def load_config(path):
        with open(path, "r") as f:
            return toml.load(f)

    ##
    # @brief wartet auf eingehende Nachrichten und verarbeitet sie.
    def listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                message = data.decode("utf-8").strip()
                print(f"[DISCOVERY] Empfangen: {message} von {addr}")
                self.handle_message(message, addr)
            except Exception as e:
                print(f"[Fehler beim Empfangen] {e}")

    ##
    # @brief verarbeitet eine eingehende Nachricht gemäß SLCP-Protokoll.
    # @param message die empfangene Nachricht.
    # @param addr die Adresse (IP, Port) des Senders.

    def handle_message(self, message, addr):
        parts = message.split()
        if not parts:
            return

        cmd = parts[0]

        if cmd == "JOIN" and len(parts) == 3:
            handle = parts[1]
            try:
                port = int(parts[2])
            except ValueError:
                print("[Fehler] Ungültiger Port in JOIN-Nachricht.")
                return
            with self.peers_lock:
                self.peers[handle] = (addr[0], port)

        elif cmd == "LEAVE" and len(parts) == 2:
            handle = parts[1]
            with self.peers_lock:
                if handle in self.peers:
                    del self.peers[handle]

        elif cmd == "WHOIS" and len(parts) == 2:
            target_handle = parts[1]
            if target_handle == self.handle:
                self.send_iam(addr)

        elif cmd == "IAM" and len(parts) == 4:
            handle = parts[1]
            ip = parts[2]
            try:
                port = int(parts[3])
            except ValueError:
                print("[Fehler] Ungültiger Port in IAM-Nachricht.")
                return
            with self.peers_lock:
                self.peers[handle] = (ip, port)

    ##
    # @brief sendet eine IAM-Nachricht mit den eigenen Informationen.
    # @param target_addr Zieladresse (IP, Port) des Empfängers.
    def send_iam(self, target_addr):
        msg = f"IAM {self.handle} {get_local_ip()} {self.port}\n"
        self.sock.sendto(msg.encode('utf-8'), target_addr)

    ##
    # @brief ermittelt die lokale IP-Adresse des Geräts.
    # @return Gibt die lokale IP-Adresse als String zurück.

    ##
    # @brief sendet JOIN-Nachricht an alle im Netzwerk (Broadcast).
    def send_join(self):
        msg = f"JOIN {self.handle} {self.port}\n"
        self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

    ##
    # @brief sendet LEAVE-Nachricht an alle im Netzwerk (Broadcast).
    def send_leave(self):
        msg = f"LEAVE {self.handle}\n"
        self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

    ##
    # @brief gibt eine thread-sichere Kopie der Peers zurück.
    # @return Kopie des Dictionaries peers.
    def get_peers(self):
        with self.peers_lock:
            return dict(self.peers)

    ##
    # @brief startet den Discovery-Dienst und beginnt mit dem Lauschen.
    def start(self):
        self.send_join()
        listener = threading.Thread(target=self.listen)
        listener.daemon = True
        listener.start()

    ##
    # @brief stoppt den Discovery-Dienst und schließt den Socket.
    def stop(self):
        self.send_leave()
        self.running = False
        self.sock.close()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


##
# Starte Discovery-Service nur, wenn Dienst nicht schon läuft.
if __name__ == "__main__":
    if is_port_in_use(BROADCAST_PORT):
        print( "[Abbruch] Discovery-Service läuft bereits(Port belegt).")
    sys.exit(1)
    Service = DiscoveryService("config.toml")
    service.start()

    print("Discovery-Service läuft. Drücke Strg+C zum Beenden.")
    try:
        while True:
            time.sleep(1)
            peers = service.get_peers()
            print("Aktuelle Peers:", service.get_peers())
    except KeyboardInterrupt:
        print("Beende Discovery-Service...")
        service.stop()