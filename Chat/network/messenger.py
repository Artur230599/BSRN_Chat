import asyncio
import socket
import time
from Chat.common import protocol
import os


class Messenger(asyncio.DatagramProtocol):
    def __init__(self, config):
        self.config = config
        self.peers = {}  # handle → (ip, port)
        self.transport = None
        self.message_callback = None
        self.image_callback = None
        self.knownusers_callback = None

    async def start_listener(self):
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(5)
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: self,
            local_addr=('0.0.0.0', self.config.port),
            family=socket.AF_INET,
            proto=socket.IPPROTO_UDP,
            allow_broadcast=True
        )
        print(f"[Messenger] Listening on port {self.config.port}")
        await asyncio.sleep(1)
        await self.send_join()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        try:
            message = data.decode()
            asyncio.create_task(self.handle_message(message, addr))
        except Exception as e:
            print(f"[Error] Could not decode message from {addr}: {e}")

    async def handle_message(self, message, addr):
        lines = message.splitlines()
        for line in lines:
            parsed = protocol.parse_slcp(line)

            if parsed["type"] == "JOIN":
                self.peers[parsed["handle"]] = (addr[0], parsed["port"])
                print(f"[JOIN] {parsed['handle']} joined from port {parsed['port']}")

            elif parsed["type"] == "LEAVE":
                self.peers.pop(parsed["handle"], None)
                print(f"[LEAVE] {parsed['handle']} has left.")

            elif parsed["type"] == "WHO":
                await self.send_known_to(addr[0], addr[1])
                print(f"[KNOWNUSERS] Sent to {addr[0]}:{addr[1]}")

            elif parsed["type"] == "KNOWNUSERS":
                user_list = message[len("KNOWNUSERS "):].strip().split(",")
                users = []
                for entry in user_list:
                    infos = entry.strip().split()
                    if len(infos) == 3:
                        handle, ip, port = infos
                        users.append((handle, ip, int(port)))
                        if handle != self.config.handle:
                            self.peers[handle] = (ip, int(port))

                # Interface-Callback aufrufen, falls vorhanden
                if self.knownusers_callback:
                    await self.knownusers_callback(users)
                else:
                    print("\n[PEER LIST] Users online:")
                    for handle, ip, port in users:
                        print(f" - {handle} @ {ip}:{port}")


            elif parsed["type"] == "MSG":
                if parsed["to"] == self.config.handle:
                    msg = parsed["message"]
                    sender = addr[0]
                    if self.message_callback:
                        await self.message_callback(sender, msg)
                    else:
                        print(f"[{sender}] {msg}")
                    if self.config.autoreply:
                        await self.send_message(sender, self.config.autoreply)

            elif parsed["type"] == "IMG":
                if parsed["to"] == self.config.handle:
                    size = int(parsed["size"])
                    try:
                        filename = await self.receive_image(addr, size)
                        if self.image_callback:
                            await self.image_callback(addr[0], filename)
                        else:
                            print(f"[Image] Received and saved to: {filename}")
                    except Exception as e:
                        print(f"[Image] Error while receiving image: {e}")

    async def send_slcp(self, line, ip, port):
        try:
            if self.transport:
                self.transport.sendto(line.encode(), (ip, port))
        except Exception as e:
            print(f"[Error] Failed to send to {ip}:{port}: {e}")

    async def send_broadcast(self, line):
        await self.send_slcp(line, "255.255.255.255", self.config.port)

    async def send_join(self):
        msg = protocol.create_join(self.config.handle, self.config.port)
        await self.send_broadcast(msg)

    async def send_leave(self):
        msg = protocol.create_leave(self.config.handle)
        await self.send_broadcast(msg)

    async def send_who(self):
        msg = "WHO\n"
        await self.send_broadcast(msg)

    async def send_message(self, handle, message):
        if handle not in self.peers:
            print(f"[Error] No known peer with handle '{handle}'")
            return
        msg = protocol.create_msg(handle, message)
        ip, port = self.peers[handle]
        await self.send_slcp(msg, ip, port)

    async def send_image(self, handle, filepath):
        if handle not in self.peers:
            print(f"[Error] No known peer with handle '{handle}'")
            return

        if not os.path.isfile(filepath):
            print(f"[Error] File '{filepath}' not found.")
            return
            # File einlesen
        with open(filepath, "rb") as f:
            img_bytes = f.read()
        size = len(img_bytes)

        # IMG Befehl erstellen und senden
        msg = f"IMG {handle} {size}\n"
        ip, port = self.peers[handle]
        await self.send_slcp(msg, ip, port)

        # Bilddaten senden
        self.transport.sendto(img_bytes, (ip, port))
        print(f"[IMG] Sent image ({size} bytes) to {handle} ({ip}:{port})")

    async def receive_image(self, addr, size):
        loop = asyncio.get_running_loop()
        sock = self.transport.get_extra_info("socket")
        img_data = b""
        # Stelle sicher, dass genau 'size' Bytes empfangen werden
        while len(img_data) < size:
            packet, _ = await loop.sock_recvfrom(sock, min(8192, size - len(img_data)))
            img_data += packet

        # Zielverzeichnis vorbereiten und Dateinamen generieren
        os.makedirs(self.config.imagepath, exist_ok=True)
        filename = os.path.join(
            self.config.imagepath,
            f"{addr[0]}_{int(time.time())}_image.jpg"
        )
        with open(filename, "wb") as f:
            f.write(img_data[:size])  # Write exactly 'size' bytes

        print(f"[IMG] Image saved as: {filename}")
        return filename

    def set_message_callback(self, callback):
        self.message_callback = callback

    def set_image_callback(self, callback):
        self.image_callback = callback

    def set_knownusers_callback(self, callback):
       self.knownusers_callback = callback

    async def send_known_to(self, ip, port):
        user_infos = [f"{self.config.handle} {self.get_local_ip()} {self.config.port}"]
        for handle, (peer_ip, peer_port) in self.peers.items():
            user_infos.append(f"{handle} {peer_ip} {peer_port}")  # peer_ip statt ip
        msg = "KNOWNUSERS " + ", ".join(user_infos) + "\n"
        await self.send_slcp(msg, ip, port)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
