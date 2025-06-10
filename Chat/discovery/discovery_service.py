import socket
import threading
import toml
import time
import sys
import errno

# Port, auf dem der Broadcast gesendet und empfangen wird
BROADCAST_PORT = 4000
# Maximale Größe des Puffers beim Empfang von Nachrichten
BUFFER_SIZE = 1024


##
# @brief prüft, ob ein bestimmter TCP-Port bereits auf dem System belegt ist.
#
# Dies wird verwendet, um zu verhindern, dass der Discovery-Dienst mehrfach gestartet wird.
#
# @param port der Port, der überprüft werden soll.
# @return True, wenn der Port bereits belegt ist, sonst False.
def is_port_in_use(port: object) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Versuche den Socket an den Port zu binden (0.0.0.0 = alle Interfaces)
        s.bind(("0.0.0.0", port))
        s.close()  # Wenn erfolgreich, schließe den Socket wieder
        return False  # Port ist frei
    except socket.error as e:
        # Wenn ein Fehler auftritt, ist der Port wahrscheinlich belegt
        return e.errno == errno.EADDRINUSE


##
# @class DiscoveryService
# @brief diese Klasse ermöglicht das Finden (Discovery) von Peers über UDP-Broadcast im lokalen Netzwerk.

class DiscoveryService:
    ##
    # @brief konstruktor : Initialisiert alle Variablen und öffnet den UDP-Socket.
    #
    # @param config_path Der Pfad zur TOML- Konfigurationsdatei (.toml)
    def __init__(self, config_path):
        self.peers = {}  # Speichert bekannte Peers als Dictionary: {handle: (IP, Port)}
        self.peers_lock = threading.Lock()  # Lock, um Thread-sicheren Zugriff auf peers zu gewährleisten
        self.running = True  # Flag, um die Listener-Schleife zu kontrollieren
        self.config = self.load_config(config_path)  # Konfiguration laden
        self.handle = self.config["handle"]  # Eigener Benutzername/Handle
        self.port = self.config["port"]  # Eigener Port, auf dem man erreichbar ist
        self.whois_port = self.config["whoisport", 0]  # Optionaler Port für WHOIS-Anfragen.

        # UDP-Socket zum Senden und Empfangen von Broadcast-Nachrichten erzeugen
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Erlaube das Senden von Broadcast-Nachrichten
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Binde den Socket an den Broadcast-Port (alle Interfaces)
        self.sock.bind(('', BROADCAST_PORT))

    ##
    # @brief Lädt die Konfiguration aus einer TOML-Datei.
    #
    # @param path Der Dateipfad zur Konfigurationsdatei.
    # @return Ein Dictionary mit den geladenen Konfigurationswerten.
    @staticmethod
    def load_config(path):
        with open(path, "r") as f:
            return toml.load(f)

    ##
    # @brief wartet auf eingehende Nachrichten und verarbeitet diese.
    def listen(self):
        while self.running:
            try:
                # Empfang von Daten(Bytes)und Adresse (IP, Port) des Senders
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                # Dekodiere die empfangenen Bytes in einen String und entferne Leerzeichen
                message = data.decode("utf-8").strip()
                print(f"[DISCOVERY] Empfangen: {message} von {addr}")
                # Verarbeite die Nachricht weiter
                self.handle_message(message, addr)
            except Exception as e:
                print(f"[Fehler beim Empfangen] {e}")

    ##
    # @brief verarbeitet eine empfangene Nachricht nach dem SLCP-Protokoll.
    #
    # @param message die empfangene Nachricht als String.
    # @param addr die Adresse (IP, Port) des Senders.

    def handle_message(self, message, addr):
        parts = message.split()  # nachricht in einzelne Worte zerlegen
        if not parts:
            return  # Leere Nachricht ignorieren

        cmd = parts[0]  # Befehl steht immer an erster Stelle

        if cmd == "JOIN" and len(parts) == 3:
            # JOIN Nachricht bedeutet, ein Peer meldet sich an
            handle = parts[1]  # Benutzername des Peers
            try:
                port = int(parts[2])  # Port des Peers
            except ValueError:
                print("[Fehler] Ungültiger Port in JOIN-Nachricht.")
                return
            with self.peers_lock:
                self.peers[handle] = (addr[0], port)  # Peer speichern

        elif cmd == "LEAVE" and len(parts) == 2:
            # LEAVE Nachricht bedeutet, einPeer verlässt das Netzwerk
            handle = parts[1]
            with self.peers_lock:
                if handle in self.peers:
                    del self.peers[handle]  # Peer entfernen

        elif cmd == "WHOIS" and len(parts) == 2:
            # WHOIS Nachricht fragt nach einem bestimmten Peer
            target_handle = parts[1]
            if target_handle == self.handle:
                # Wenn der eigene Handle gefragt ist, antworte mit IAM
                self.send_iam(addr)

        elif cmd == "IAM" and len(parts) == 4:
            # IAM Nachricht enthält die Informationen eines Peers als Antwort auf WHOIS
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
    # @brief sendet eine IAM-Nachricht an einen bestimmten Empfänger.
    #
    # Die IAM-Nachricht teilt dem Empfänger mit, dass dieser Peer existiert und welche IP und Port er hat.
    #
    # @param target_addr Tuple (IP, Port) des Empfängers.
    def send_iam(self, target_addr):
        msg = f"IAM {self.handle} {self.get_local_ip()} {self.port}\n"  # Nachricht formatieren
        self.sock.sendto(msg.encode('utf-8'), target_addr)  # Nachricht senden

    ##
    # @brief ermittelt die lokale IP-Adresse des Geräts.
    #
    # Dies geschieht, indem eine Verbindung zu einem öffentlichen DNS-Server hergestellt wird.
    #
    # @return Gibt die lokale IP-Adresse als String zurück.
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Verbindung zu Google DNS (8.8.8.8) aufbauen (port 80)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]  # Eigene IP-Adresse aus dem Socket lesen
            s.close()
            return ip
        except Exception:
            # Wenn das nicht klappt, localhost zurückgeben
            return "127.0.0.1"

        ##
        # @brief sendet eine JOIN-Nachricht an alle im Netzwerk per broadcast.
        #
        # Diese Nachricht informiert andere Peers darüber, dass dieser Peer jetzt online ist.
        def send_join(self):
            msg = f"JOIN {self.handle} {self.port}\n"
            self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

        ##
        # @brief sendet eine LEAVE-Nachricht an alle im Netzwerk per Broadcast.
        #
        # Diese Nachricht informiert andere Peers darüber, dass dieser Peer offline geht.
        def send_leave(self):
            msg = f"LEAVE {self.handle}\n"
            self.sock.sendto(msg.encode("utf-8"), ('255.255.255.255', BROADCAST_PORT))

        ##
        # @brief gibt eine sichere Kopie aller aktuell bekannten Peers zurück.
        #
        # @return Ein Dictionary mit Peers {handle: (IP, Port)}.
        def get_peers(self):
            with self.peers_lock:
                return dict(self.peers)  # Kopie zurückgeben, damit andere Threads nicht stören

        ##
        # @brief startet den Discovery-Service.
        #
        # Sendet eine JOIN-Nachricht und startet einen Hintergrund-Thread, der auf Nachrichten hört.
        def start(self):
            self.send_join()  # Anderen mitteilen, dass man online ist
            listener = threading.Thread(target=self.listen)  # Listener-Thread erzeugen
            listener.daemon = True  # Damit der Thread beendet wird, wenn das Hauptprogramm endet
            listener.start()  # Thread starten

        ##
        # @brief stoppt den Discovery-Service.
        #
        # Sendet eine LEAVE-Nachricht und beendet die Listener-Schleife.
        def stop(self):
            self.send_leave()  # Anderen mitteilen, dass man offline geht
            self.running = False  # Listener stoppen
            self.sock.close()  # Socket schließen

        ##
        # @brief Hauptprogramm startet den DiscoveryService, wenn der Broadcast-Port frei ist.
        if __name__ == "__main__":
            if is_port_in_use(BROADCAST_PORT):
                print("[Abbruch] Discovery-Service läuft bereits (Port belegt).")
                sys.exit(1)
        service = DiscoveryService("config.toml")  # Service mit Konfig laden
        service.start()  # Service starten

        print("Discovery-Service läuft. Drücke Strg+C zum Beenden.")
        try:
            while True:
                time.sleep(1)  # Warte 1 Sekunde
                peers = service.get_peers()  # Bekannte Peers abfragen
                print("Aktuelle Peers:", peers)
        except KeyboardInterrupt:
            print("Beende Discovery-Service...")
            service.stop()
