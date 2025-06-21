import socket  # Für Netzwerkkommunikation (UDP/TCP Sockets)
import threading  # Für nebenläufige Threads (z.B. Listener Thread)
import toml  # Zum Laden der TOML-Konfigurationsdatei
import time  # Für Zeitfunktionen wie sleep
import sys  # Für Systemfunktionen, z.B. Programm beenden
import errno  # Für Fehlerspezifische Nummern (z.B. Port belegt)

BROADCAST_PORT = 4000
BUFFER_SIZE = 1024

def is_port_in_use(port: int) -> bool:
    """
    @brief Prüft, ob ein TCP-Port bereits belegt ist.

    @param port TCP-Portnummer, die geprüft werden soll
    @return True, wenn der Port belegt ist, sonst False
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Erstelle TCP Socket
    try:
        s.bind(("0.0.0.0", port))  # Versuche den Port zu binden (0.0.0.0 = alle Schnittstellen)
        s.close()  # Wenn erfolgreich, schließe Socket und gib False zurück (Port frei)
        return False
    except socket.error as e:
        # Falls Fehler, prüfe ob Fehlernummer "Adresse bereits vergeben" (Port belegt) ist
        return e.errno == errno.EADDRINUSE

class DiscoveryService:
    """
    @class DiscoveryService
    @brief Implementiert den Discovery-Dienst für das dezentrale Chat-System.

    Verwaltet bekannte Peers, sendet und empfängt UDP Broadcast-Nachrichten.
    """

    def __init__(self, config_path):
        """
        @brief Konstruktor für den DiscoveryService.

        Lädt Konfiguration, initialisiert Variablen und bindet UDP Socket.

        @param config_path Pfad zur TOML-Konfigurationsdatei
        """
        self.peers = {}
        self.peers_lock = threading.Lock()
        self.running = True

        self.config = self.load_config(config_path)

        print("[DEBUG] Geladene Konfiguration:", self.config)

        try:
            self.handle = self.config["handle"]  # Benutzername/Handle
            self.port = int(self.config["port"]) # TCP-Port als Integer
        except KeyError as e:
            print(f"[Fehler] Fehlender Eintrag in TOML-Datei: {e}")
            sys.exit(1)

        self.whois_port = self.config.get("whoisport", 0)  # Optionaler Whois-Port

        # UDP-Socket erstellen und für Broadcast konfigurieren
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', BROADCAST_PORT))  # An alle Interfaces binden, Broadcast-Port

    @staticmethod
    def load_config(path):
        """
        @brief Lädt eine TOML-Konfigurationsdatei.

        @param path Pfad zur TOML-Datei
        @return Dictionary mit Konfigurationsdaten oder leeres Dict bei Fehler
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                return toml.load(f)
        except Exception as e:
            print(f"[Fehler] Konfigurationsdatei konnte nicht geladen werden: {e}")
            return {}

    def listen(self):
        """
        @brief Endlosschleife zum Empfangen und Verarbeiten von UDP-Nachrichten.

        Läuft in eigenem Thread, verarbeitet JOIN, LEAVE, WHO und KNOWNUSERS Nachrichten.
        """
        while self.running:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                message = data.decode("utf-8").strip()

                print(f"[DISCOVERY] Empfangen: {message} von {addr}")
                self.handle_message(message, addr)
            except Exception as e:
                print(f"[Fehler beim Empfangen] {e}")

    def handle_message(self, message, addr):
        """
        @brief Verarbeitet eingehende UDP-Nachrichten gemäß Protokoll.

        @param message Empfangene Nachricht als String
        @param addr Adresse des Senders (IP, Port)
        """
        parts = message.split()
        if not parts:
            return

        cmd = parts[0]

        if cmd == "JOIN" and len(parts) == 3:
            handle = parts[1]
            ip = addr[0]
            try:
                tcp_port = int(parts[2])
                with self.peers_lock:
                    self.peers[handle] = (ip, tcp_port)
            except ValueError:
                print("[Fehler] Ungültiger Port in JOIN.")

        elif cmd == "LEAVE" and len(parts) == 2:
            handle = parts[1]
            with self.peers_lock:
                self.peers.pop(handle, None)

        elif cmd == "WHO" and len(parts) == 1:
            with self.peers_lock:
                seen = set()
                user_infos = []

                for handle, (ip, port) in self.peers.items():
                    entry = f"{handle} {ip} {port}"
                    if entry not in seen and (handle != self.handle or ip != self.get_local_ip() or port != self.port):
                        user_infos.append(entry)
                        seen.add(entry)

                self_info = f"{self.handle} {self.get_local_ip()} {self.port}"
                if self_info not in seen:
                    user_infos.append(self_info)

            msg = "KNOWNUSERS " + ", ".join(user_infos) + "\n"
            self.sock.sendto(msg.encode("utf-8"), addr)

        elif cmd == "KNOWNUSERS" and len(parts) >= 2:
            user_str = message[len("KNOWNUSERS "):].strip()
            user_list = [u.strip() for u in user_str.split(",") if u.strip()]

            print("[DISCOVERY] KNOWNUSERS-Liste:")

            with self.peers_lock:
                seen = set()
                for entry in user_list:
                    infos = entry.strip().split()
                    if len(infos) != 3:
                        print(f"[WARNUNG] Ungültiger KNOWNUSERS-Eintrag: {entry}")
                        continue

                    handle, ip, port = infos
                    # TODO: Bekannte Peers hier verarbeiten

    def send_who(self):
        """
        @brief Sendet eine WHO-Anfrage als UDP-Broadcast, um bekannte Peers abzufragen.
        """
        msg = "WHO\n"
        print("[DEBUG] sende WHO-Broadcast...")
        self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

    def get_local_ip(self):
        """
        @brief Ermittelt die lokale IP-Adresse des Hosts.

        @return String mit der lokalen IP-Adresse
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def send_join(self):
        """
        @brief Sendet eine JOIN-Nachricht als Broadcast, um sich anzumelden.
        """
        msg = f"JOIN {self.handle} {self.port}\n"
        self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

    def send_leave(self):
        """
        @brief Sendet eine LEAVE-Nachricht als Broadcast, um sich abzumelden.
        """
        msg = f"LEAVE {self.handle}\n"
        self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

    def get_peers(self):
        """
        @brief Gibt eine Kopie der aktuellen Peer-Liste zurück.

        @return Dictionary mit Peers {handle: (IP, Port)}
        """
        with self.peers_lock:
            return dict(self.peers)

    def start(self):
        """
        @brief Startet den Discovery-Service: Listener-Thread, JOIN und WHO senden.
        """
        listener = threading.Thread(target=self.listen)
        listener.daemon = True
        listener.start()

        time.sleep(0.5)

        self.send_join()
        time.sleep(0.5)
        self.send_who()

    def stop(self):
        """
        @brief Stoppt den Discovery-Service, sendet LEAVE und schließt das Socket.
        """
        self.send_leave()
        self.running = False
        self.sock.close()

if __name__ == "__main__":
    """
    @brief Hauptprogramm: Prüft Port, startet Discovery-Service, zeigt Peers an.
    """
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
        print("Beende Discovery-Service....")
        service.stop()
