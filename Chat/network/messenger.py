"""
@file messenger.py
@brief Messenger-Klasse für das SLCP-Chat-Projekt.
@details
    Diese Klasse implementiert die UDP- und TCP-Kommunikation für den Austausch von Nachrichten und Bildern
    im dezentralen Chat. Sie verwaltet Peers, verarbeitet SLCP-Nachrichten und stellt Methoden zum Senden
    und Empfangen bereit.
"""

import asyncio
import mimetypes
import socket
import time
from Chat.common import protocol
import os


class Messenger(asyncio.DatagramProtocol):
    """
    @class Messenger
    @brief Messenger für den Versand und Empfang von Chat-Nachrichten und Bildern.
    @details
        Verwaltet alle UDP- und TCP-Kommunikationsprozesse, Peer-Liste, sowie das Senden und Empfangen von Nachrichten und Bildern.
        Stellt zudem verschiedene Callback-Funktionen für die Interaktion mit der Benutzeroberfläche bereit.
    """
    def __init__(self, config):
        """
        @brief Konstruktor der Messenger-Klasse
        @param config Konfigurationsobjekt mit folgenden Attributen:
            - handle: Benutzername
            - port: Port für TCP/UDP Kommunikation
            - whoisport: Port für WHO-Broadcasts
            - imagepath: Pfad zum Speichern empfangener Bilder
            - autoreply: Automatische Antwort (optional)
        """
        self.config = config
        self.peers = {}  # Dictionary: handle → (ip, port) - Bekannte Peers
        self.transport = None # UDP Transport Objekt
        self.message_callback = None  # Callback für eingehende Nachrichten
        self.image_callback = None  # Callback für empfangene Bilder
        self.knownusers_callback = None  # Callback für Benutzerlisten
        self.progress_callback = None  # Callback für Übertragungsfortschritt
        self.pending_who_responses = {}  # Ausstehende WHO-Antworten
        self.who_timeout = 2.0  # Timeout für WHO-Anfragen in Sekunden

    async def start_listener(self):
        """
        @brief Startet den UDP-Listener und den TCP-Server.
        @details
            Öffnet den UDP-Socket für Nachrichtenempfang und startet
            parallel den TCP-Server für den Empfang von Bildern.
        """
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(5)

        asyncio.create_task(self.start_tcp_server())
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: self,
            local_addr=('0.0.0.0', self.config.port),
            family=socket.AF_INET,
            proto=socket.IPPROTO_UDP,
            allow_broadcast=True
        )
        print(f"[Messenger] Lauscht auf Port {self.config.port}")
        await asyncio.sleep(1)
        await self.send_join()

    def connection_made(self, transport):
        """
        @brief Wird aufgerufen, wenn die UDP-Verbindung erfolgreich hergestellt wurde.
        @param transport Das UDP-Transport-Objekt
        """
        self.transport = transport

    def datagram_received(self, data, addr):
        """
        @brief Wird aufgerufen, wenn eine UDP-Nachricht empfangen wird.
        @param data Empfangene Bytes (Nachricht)
        @param addr Adresse des Absenders als Tupel (IP, Port)
        """
        try:
            message = data.decode()
            asyncio.create_task(self.handle_message(message, addr))
        except Exception as e:
            print(f"[Error] Konnte Nachricht von {addr} nicht dekodieren: {e}")

    async def handle_message(self, message, addr):
        """
        @brief Verarbeitet empfangene SLCP-Nachrichten.
        @param message Die dekodierte Nachricht als String
        @param addr Absender-Adresse als (ip, port) Tupel
        @details Parst SLCP-Befehle und führt entsprechende Aktionen aus:
            - JOIN: Neuen Peer registrieren
            - LEAVE: Peer entfernen
            - WHO: Bekannte Benutzer senden
            - KNOWNUSERS: Benutzerliste verarbeiten
            - MSG: Private Nachricht empfangen
            - IMG: Bildübertragung initialisieren
        """
        lines = message.splitlines()
        for line in lines:
            parsed = protocol.parse_slcp(line)

            if parsed["type"] == "JOIN":
                self.peers[parsed["handle"]] = (addr[0], parsed["port"])
                print(f"[JOIN] {parsed['handle']} ist vom Port {parsed['port']} beigetreten")

            elif parsed["type"] == "LEAVE":
                self.peers.pop(parsed["handle"], None)
                print(f"[LEAVE] {parsed['handle']} hat den Chat verlassen.")

            elif parsed["type"] == "WHO":
                await self.send_known_to(addr[0], addr[1])
                print(f"[KNOWNUSERS] Gesendet an {addr[0]}:{addr[1]}")

            elif parsed["type"] == "KNOWNUSERS":
                await self.handle_knownusers_response(message, addr)

            elif parsed["type"] == "MSG":
                if parsed["to"] == self.config.handle:
                    msg = parsed["message"]
                    sender_ip, sender_port = addr[0], addr[1]
                    sender_handle = None

                    # Absender-Handle ermitteln
                    for handle, (ip, port) in self.peers.items():
                        if ip == sender_ip and port == sender_port:
                            sender_handle = handle
                            break
                    if not sender_handle:
                        for handle, (ip, _) in self.peers.items():
                            if ip == sender_ip:
                                sender_handle = f"{handle} (port {sender_port})"
                                break

                    sender_display = sender_handle if sender_handle else f"Unbekannt ({sender_ip}:{sender_port})"

                    # Nachricht-Callback aufrufen oder ausgeben
                    if self.message_callback:
                        await self.message_callback(sender_display, msg)
                    else:
                        print(f"\n💬 Nachricht von {sender_display}: {msg}")

                    # Automatische Antwort senden falls konfiguriert
                    if self.config.autoreply:
                        await self.send_message(sender_display, self.config.autoreply)

            elif parsed["type"] == "IMG":
                if parsed["to"] == self.config.handle:
                    print(f"[IMG] Peer {addr[0]} sendet ein Bild über TCP ...")

    async def send_slcp(self, line, ip, port):
        """
        @brief Sendet eine SLCP-Nachricht (UDP) an die angegebene Zieladresse.
        @param line SLCP-formatierte Nachricht (String)
        @param ip Ziel-IP-Adresse
        @param port Ziel-Portnummer
        """
        try:
            if self.transport:
                self.transport.sendto(line.encode(), (ip, port))
        except Exception as e:
            print(f"[Error] Fehler beim Senden an {ip}:{port}: {e}")

    async def send_broadcast(self, line):
        """
        @brief Sendet eine SLCP-Broadcast-Nachricht an alle Teilnehmer im lokalen Netzwerk.
        @param line Die zu sendende SLCP-Nachricht (String)
        """
        await self.send_slcp(line, "255.255.255.255", self.config.whoisport)

    async def send_join(self):
        """
        @brief Sendet eine JOIN-Nachricht per UDP-Broadcast, um dem Chat beizutreten.
        """
        msg = protocol.create_join(self.config.handle, self.config.port)
        await self.send_broadcast(msg)

    async def send_leave(self):
        """
        @brief Sendet eine LEAVE-Nachricht per UDP-Broadcast, um den Chat zu verlassen.
        """
        msg = protocol.create_leave(self.config.handle)
        await self.send_broadcast(msg)

    async def send_who(self):
        """
        @brief Sendet eine WHO-Nachricht, um die Liste aktiver Teilnehmer zu erfragen.
        """
        msg = "WHO\n"
        await self.send_broadcast(msg)

    async def send_message(self, handle, message):
        """
        @brief Sendet eine Textnachricht an einen bestimmten Peer.
        @param handle Ziel-Handle (Benutzername) des Empfängers
        @param message Die zu sendende Nachricht (String)
        """
        if handle not in self.peers:
            print(f"[Error] Kein bekannter Peer mit Handle '{handle}'")
            return
        if handle in self.peers:
            ip, port = self.peers[handle]
            msg = protocol.create_msg(handle, message)
            await self.send_slcp(msg, ip, port)
        else:
            print(f"[Error] Handle '{handle}' ist nicht verbunden")

    async def send_image(self, handle, filepath):
        """
        @brief Sendet ein Bild an einen bestimmten Peer via TCP.
        @param handle Der Ziel-Benutzername
        @param filepath Pfad zur Bilddatei
        @return True bei Erfolg, False bei Fehler
        @details Überprüft die Datei auf Gültigkeit, öffnet eine TCP-Verbindung
                 zum Ziel-Peer und überträgt das Bild in Chunks.
        """
        if handle not in self.peers:
            print(f"[Error] Kein bekannter Peer mit Handle '{handle}'")
            return

        if not os.path.isfile(filepath):
            print(f"[Error] Datei '{filepath}' nicht gefunden.")
            return

        try:
            with open(filepath, "rb") as f:
                img_bytes = f.read()
            size = len(img_bytes)

            mime_type, _ = mimetypes.guess_type(filepath)
            if not mime_type or not mime_type.startswith('image/'):
                print(f"[Error] Datei '{filepath}' ist kein gültiges Bild.")
                return False

            print(f"[IMG] Bereite das Senden von {size} Bytes an {handle} vor")

            ip, port = self.peers[handle]
            loop = asyncio.get_running_loop()

            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.setblocking(False)

            try:
                await asyncio.wait_for(
                    loop.sock_connect(tcp_socket, (ip, port)),
                    timeout=10.0  # 10 seconds timeout
                )

                img_command = f"IMG {handle} {size}\n".encode('utf-8')
                await loop.sock_sendall(tcp_socket, img_command)

                await self.send_image_data(tcp_socket, img_bytes, handle)

                print(f"[IMG] Bild erfolgreich gesendet ({size} Bytes) an {handle}")
                return True

            except asyncio.TimeoutError:
                print(f"[Error] Verbindung zu {handle} abgelaufen")
                return False
            except ConnectionRefusedError:
                print(f"[Error] Verbindung zu {handle} wurde abgelehnt")
                return False
            finally:
                tcp_socket.close()

        except Exception as e:
            print(f"[Error] Bild konnte nicht gesendet werden: {e}")
            return False

    async def send_image_data(self, tcp_socket, img_bytes, handle):
        """
        @brief Sendet die Binärdaten eines Bildes über einen TCP-Socket und ruft Progress-Callbacks auf.
        @param tcp_socket Offener TCP-Socket
        @param img_bytes Bilddaten als Byte-Array
        @param handle Ziel-Handle des Empfängers (für Progress-Callback)
        """
        loop = asyncio.get_running_loop()
        total_size = len(img_bytes)
        sent = 0
        chunk_size = 8192  # 8KB Chunks

        while sent < total_size:
            current_chunk_size = min(chunk_size, total_size - sent)
            chunk = img_bytes[sent:sent + current_chunk_size]

            await loop.sock_sendall(tcp_socket, chunk)
            sent += current_chunk_size

            # Progress-Callback aufrufen
            if self.progress_callback is not None:
                progress = (sent / total_size) * 100
                if asyncio.iscoroutinefunction(self.progress_callback):
                    await self.progress_callback("send", handle, progress, sent, total_size)
                else:
                    self.progress_callback("send", handle, progress, sent, total_size)

            if sent < total_size:
                await asyncio.sleep(0.001)

    async def start_tcp_server(self):
        """
        @brief Startet den TCP-Server zum Empfang von eingehenden Bildübertragungen.
        """
        try:
            server = await asyncio.start_server(
                self.handle_tcp_connection,
                '0.0.0.0',
                self.config.port
            )
            print(f"[TCP] Server gestartet auf Port {self.config.port}")

            async with server:
                await server.serve_forever()

        except Exception as e:
            print(f"[Error] TCP-Server konnte nicht gestartet werden: {e}")

    async def handle_tcp_connection(self, reader, writer):
        """
        @brief Behandelt eingehende TCP-Verbindungen für Bildempfang.
        @param reader StreamReader für eingehende Daten
        @param writer StreamWriter für ausgehende Daten
        @details Liest IMG-Befehle und empfängt Bilddaten, speichert diese
                 lokal und ruft Image-Callbacks auf.
        """
        addr = writer.get_extra_info('peername')
        print(f"[TCP] Neue Verbindung von {addr}")

        try:
            img_command_bytes = await asyncio.wait_for(
                reader.readuntil(b'\n'),
                timeout=5.0
            )
            img_command = img_command_bytes.decode('utf-8').strip()

            if img_command.startswith("IMG"):
                parts = img_command.split()
                if len(parts) >= 3:
                    _, handle, size_str = parts[0], parts[1], parts[2]
                    size = int(size_str)
                    print(f"[IMG] Empfange {size} Bytes vom Peer {addr[0]}")
                    filename = await self.receive_image_data(reader, addr, size, handle)

                    if filename is not None and self.image_callback is not None:
                        try:
                            if asyncio.iscoroutinefunction(self.image_callback):
                                await self.image_callback(handle, filename)
                            else:
                                self.image_callback(handle, filename)
                        except Exception as e:
                            print(f"[Error] Fehler beim Bild-Callback: {str(e)}")
                else:
                    print(f"[Error] Ungültiges IMG-Befehlsformat: {img_command}")
            else:
                print(f"[Error] Unbekannter TCP-Befehl: {img_command}")

        except asyncio.TimeoutError:
            print(f"[Error] TCP-Verbindung von {addr} abgelaufen")
        except Exception as e:
            print(f"[Error] TCP-Verbindungsfehler von {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def receive_image_data(self, reader, addr, size, sender_handle):
        """
        @brief Empfängt Bilddaten über TCP und speichert sie.
        @param reader StreamReader für die Datenübertragung
        @param addr Absender-Adresse als (ip, port) Tupel
        @param size Erwartete Dateigröße in Bytes
        @param sender_handle Benutzername des Absenders
        @return Dateiname der gespeicherten Datei oder None bei Fehler
        @details Empfängt Daten in Chunks, zeigt Fortschritt an und speichert
                das Bild mit einem eindeutigen Dateinamen.
        """
        try:
            img_data = bytearray()
            received = 0

            # Daten in Chunks empfangen
            while received < size:
                chunk = await asyncio.wait_for(
                    reader.read(min(8192, size - received)),
                    timeout=30.0
                )
                if not chunk:
                    print(f"[Error] Verbindung wurde unerwartet geschlossen")
                    return None

                img_data += chunk
                received += len(chunk)

                # Progress-Callback aufrufen
                if self.progress_callback is not None:
                    progress = (received / size) * 100
                    if asyncio.iscoroutinefunction(self.progress_callback):
                        await self.progress_callback("receive", sender_handle, progress, received, size)
                    else:
                        self.progress_callback("receive", sender_handle, progress, received, size)

             # Eindeutigen Dateinamen generieren
            filename = os.path.join(
                self.config.imagepath,
                f"{addr[0]}_{int(time.time())}_{sender_handle}.jpg"
            )
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # Datei speichern
            with open(filename, "wb") as f:
                f.write(img_data)
            print(f"[IMG] Gespeichert als: {os.path.normpath(filename)}")
            return filename

        except Exception as e:
            print(f"[Error] Fehler beim Empfangen des Bildes: {e}")
            return None

    def set_progress_callback(self, callback):
        """
        @brief Setzt den Callback für Übertragungsfortschritt.
        @param callback Funktion mit Signatur: (direction, handle, progress, bytes_transferred, total_bytes)
            - direction: "send" oder "receive"
            - handle: Benutzername des Partners
            - progress: Fortschritt in Prozent (0-100)
            - bytes_transferred: Übertragene Bytes
            - total_bytes: Gesamtanzahl Bytes
        """
        self.progress_callback = callback

    def set_message_callback(self, callback):
        """
        @brief Setzt den Callback für empfangene Nachrichten.
        @param callback Async-Funktion mit Signatur: (sender_handle, message)
        """
        self.message_callback = callback

    def set_image_callback(self, callback):
        """
        @brief Setzt den Callback für empfangene Bilder.
        @param callback Funktion mit Signatur: (sender_handle, filename)
        """
        self.image_callback = callback

    def set_knownusers_callback(self, callback):
        """
        @brief Setzt den Callback für Benutzerlisten.
        @param callback Async-Funktion mit Signatur: (users_list)
            users_list ist eine Liste von (handle, ip, port) Tupeln
        """
        self.knownusers_callback = callback

    async def handle_knownusers_response(self, message, addr):
        """
        @brief Verarbeitet KNOWNUSERS-Antworten.
        @param message Die vollständige KNOWNUSERS-Nachricht
        @param addr Absender-Adresse als (ip, port) Tupel
        @details Parst die Benutzerliste, aktualisiert die Peer-Informationen
                und ruft den entsprechenden Callback auf. Sammelt Antworten
                für eine kurze Zeit um mehrfache Antworten zu konsolidieren.
        """
        user_list = message[len("KNOWNUSERS "):].strip().split(",")
        users = []
        for entry in user_list:
            infos = entry.strip().split()
            if len(infos) == 3:
                handle, ip, port = infos
                users.append((handle, ip, int(port)))
                if handle != self.config.handle:
                    self.peers[handle] = (ip, int(port))

        response_id = f"who_{int(time.time())}"
        if response_id not in self.pending_who_responses:
            self.pending_who_responses[response_id] = []

        self.pending_who_responses[response_id].extend(users)

        await asyncio.sleep(0.5)

        if response_id in self.pending_who_responses:
            all_users = self.pending_who_responses[response_id]
            unique_users = {}
            for handle, ip, port in all_users:
                unique_users[handle] = (ip, port)

            if self.knownusers_callback:
                users_list = [(h, i, p) for h, (i, p) in unique_users.items()]
                await self.knownusers_callback(users_list)
            else:
                print("\n[PEER LIST] Aktive Benutzer:")
                for handle, (ip, port) in unique_users.items():
                    print(f" - {handle} @ {ip}:{port}")

            del self.pending_who_responses[response_id]

    async def send_known_to(self, ip, port):
        """
        @brief Sendet bekannte Benutzer als Antwort auf WHO-Anfrage.
        @param ip Ziel-IP-Adresse
        @param port Ziel-Port
        @details Erstellt eine KNOWNUSERS-Nachricht mit allen bekannten Peers
                inklusive eigener Informationen und sendet diese direkt an
                den anfragenden Peer.
        """
        user_infos = [f"{self.config.handle} {self.get_local_ip()} {self.config.port}"]
        for handle, (peer_ip, peer_port) in self.peers.items():
            user_infos.append(f"{handle} {peer_ip} {peer_port}")  # peer_ip statt ip
        msg = "KNOWNUSERS " + ", ".join(user_infos) + "\n"
        await self.send_slcp(msg, ip, port)

    def get_local_ip(self):
        """
        @brief Ermittelt die lokale IP-Adresse.
        @return Die lokale IP-Adresse als String
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
