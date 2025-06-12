import asyncio
import socket
from Chat.common import protocol
import os

# Messenger ist eine Klasse für die UDP-Kommunikation mit SLCP-Protokoll
# Sie basiert auf asyncio.DatagramProtocol, damit sie UDP verwenden kann
class Messenger(asyncio.DatagramProtocol):

    def __init__(self, config):
        self.config = config                     # Konfigurationsdaten aus TOML
        self.peers = {}                          # bekannte Nutzer: handle → (IP, Port)
        self.transport = None                    # UDP-Transport-Objekt
        self.message_callback = None             # Callback für empfangene Textnachrichten
        self.image_callback = None               # Callback für empfangene Bilder

    # Startet den UDP-Listener
    async def start_listener(self):
        loop = asyncio.get_running_loop()

        # UDP-Endpoint erstellen → bindet sich an lokale Adresse/Port
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: self,
            local_addr=('0.0.0.0', self.config.port),
            family=socket.AF_INET,
            proto=socket.IPPROTO_UDP,
            allow_broadcast=True
        )
        print(f"[Messenger] Listening on port {self.config.port}")
        await asyncio.sleep(1)
        await self.send_join()  # nach Start automatisch JOIN senden

    # Wird aufgerufen, wenn UDP-Verbindung erfolgreich aufgebaut wurde
    def connection_made(self, transport):
        self.transport = transport

    # Wird aufgerufen, wenn Daten empfangen wurden
    def datagram_received(self, data, addr):
        try:
            message = data.decode()  # Daten als Text (SLCP) dekodieren
            asyncio.create_task(self.handle_message(message, addr))
        except Exception as e:
            print(f"[Error] Could not decode message from {addr}: {e}")

    # Verarbeitet eingehende Nachrichtenzeilen (JOIN, MSG, IMG usw.)
    async def handle_message(self, message, addr):
        lines = message.splitlines()
        for line in lines:
            parsed = protocol.parse_slcp(line)  # SLCP-Zeile analysieren

            if parsed["type"] == "JOIN":
                # Nutzer in die Peer-Liste eintragen
                self.peers[parsed["handle"]] = (addr[0], parsed["port"])
                print(f"[JOIN] {parsed['handle']} joined from {addr[0]}:{parsed['port']}")

            elif parsed["type"] == "LEAVE":
                # Nutzer aus Peer-Liste entfernen
                self.peers.pop(parsed["handle"], None)
                print(f"[LEAVE] {parsed['handle']} has left.")

            elif parsed["type"] == "WHOIS":
                # Wenn man selbst gemeint ist → Peer-Liste senden
                if parsed["handle"] == self.config.username:
                    await self.send_known_to(addr[0], addr[1])

            elif parsed["type"] == "MSG":
                # Wenn man selbst Empfänger ist → Nachricht anzeigen oder weitergeben
                if parsed["to"] == self.config.username:
                    msg = parsed["message"]
                    sender = addr[0]
                    if self.message_callback:
                        await self.message_callback(sender, msg)
                    else:
                        print(f"[{sender}] {msg}")
                    # Autoreply senden, falls aktiviert
                    if self.config.autoreply:
                        await self.send_message(sender, self.config.autoreply)

            elif parsed["type"] == "IMG":
                # Wenn man selbst Empfänger ist → Bilddaten empfangen und speichern
                if parsed["to"] == self.config.username:
                    size = parsed["size"]
                    filename = await self.receive_image(addr, size)
                    if self.image_callback:
                        await self.image_callback(addr[0], filename)
                    else:
                        print(f"[Image] Received and saved to: {filename}")

    # Sendet eine SLCP-Nachricht an eine bestimmte IP/Port
    async def send_slcp(self, line, ip, port):
        if self.transport:
            self.transport.sendto(line.encode(), (ip, port))

    # Sendet eine SLCP-Nachricht an alle im lokalen Netzwerk
    async def send_broadcast(self, line):
        await self.send_slcp(line, "255.255.255.255", self.config.port)

    # Sendet einen JOIN-Befehl ins Netzwerk
    async def send_join(self):
        msg = protocol.create_join(self.config.username, self.config.port)
        await self.send_broadcast(msg)

    # Sendet einen LEAVE-Befehl ins Netzwerk
    async def send_leave(self):
        msg = protocol.create_leave(self.config.username)
        await self.send_broadcast(msg)

    # Sendet WHOIS für einen bestimmten Benutzer
    async def send_whois(self, handle):
        msg = protocol.create_whois(handle)
        await self.send_broadcast(msg)

    # Sendet eine Textnachricht direkt an einen Nutzer (wenn bekannt)
    async def send_message(self, handle, message):
        if handle not in self.peers:
            print(f"[Error] No known peer with handle '{handle}'")
            return
        msg = protocol.create_msg(handle, message)
        ip, port = self.peers[handle]
        await self.send_slcp(msg, ip, port)

    # Sendet ein Bild in zwei Schritten: 1. IMG-Zeile, 2. Binärdaten
    async def send_image(self, handle, filepath):
        if handle not in self.peers:
            print(f"[Error] No known peer with handle '{handle}'")
            return
        size = os.path.getsize(filepath)
        msg = protocol.create_img(handle, size)
        ip, port = self.peers[handle]
        await self.send_slcp(msg, ip, port)

        # Bilddaten im Anschluss senden
        with open(filepath, "rb") as f:
            data = f.read()
            self.transport.sendto(data, (ip, port))

    # Empfängt die Bilddaten und speichert sie lokal unter /images/
    async def receive_image(self, addr, size):
        loop = asyncio.get_event_loop()
        data, _ = await loop.sock_recvfrom(self.transport.get_extra_info("socket"), size)
        filename = f"{self.config.imagepath}/{addr[0]}_image.jpg"
        with open(filename, "wb") as f:
            f.write(data)
        return filename

    # Legt fest, welche Funktion ausgeführt wird, wenn Textnachricht empfangen wird
    def set_message_callback(self, callback):
        self.message_callback = callback

    # Legt fest, welche Funktion ausgeführt wird, wenn Bild empfangen wird
    def set_image_callback(self, callback):
        self.image_callback = callback

    # Sendet auf WHOIS-Anfrage eine Liste aller bekannten Nutzer (KNOWNUSERS)
    async def send_known_to(self, ip, port):
        users = []
        for handle, (ip_, port_) in self.peers.items():
            users.append(f"{handle} {ip_} {port_}")
        message = "KNOWNUSERS " + ", ".join(users) + "\n"
        await self.send_slcp(message, ip, port)