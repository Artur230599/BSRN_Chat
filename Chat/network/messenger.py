import asyncio
import socket
from Chat.common import protocol
import os


class Messenger(asyncio.DatagramProtocol):
    def __init__(self, config):
        self.config = config
        self.peers = {}  # handle → (ip, port)
        self.transport = None
        self.message_callback = None
        self.image_callback = None

    async def start_listener(self):
        loop = asyncio.get_running_loop()
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
                print(f"[JOIN] {parsed['handle']} joined from {addr[0]}:{parsed['port']}")

            elif parsed["type"] == "LEAVE":
                self.peers.pop(parsed["handle"], None)
                print(f"[LEAVE] {parsed['handle']} has left.")

            elif parsed["type"] == "WHOIS":
                # FIX: Vergleiche mit self.config.handle statt username
                if parsed["handle"] == self.config.handle:
                    response = protocol.create_iam(
                        self.config.handle,
                        self.get_local_ip(),
                        self.config.port
                    )
                    await self.send_slcp(response, addr[0], addr[1])

            elif parsed["type"] == "WHOIS_RESPONSE":
                self.peers[parsed["handle"]] = (parsed["ip"], parsed["port"])
                print(f"[WHOIS] {parsed['handle']} is at {parsed['ip']}:{parsed['port']}")

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
                    size = parsed["size"]
                    filename = await self.receive_image(addr, size)
                    if self.image_callback:
                        await self.image_callback(addr[0], filename)
                    else:
                        print(f"[Image] Received and saved to: {filename}")

    async def send_slcp(self, line, ip, port):
        if self.transport:
            self.transport.sendto(line.encode(), (ip, port))

    async def send_broadcast(self, line):
        await self.send_slcp(line, "255.255.255.255", self.config.port)

    async def send_join(self):
        msg = protocol.create_join(self.config.handle, self.config.port)
        await self.send_broadcast(msg)

    async def send_leave(self):
        msg = protocol.create_leave(self.config.handle)
        await self.send_broadcast(msg)

    async def send_whois(self, handle):
        msg = protocol.create_whois(handle)
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
        size = os.path.getsize(filepath)
        msg = protocol.create_img(handle, size)
        ip, port = self.peers[handle]
        await self.send_slcp(msg, ip, port)

        with open(filepath, "rb") as f:
            data = f.read()
            self.transport.sendto(data, (ip, port))

    async def receive_image(self, addr, size):
        loop = asyncio.get_event_loop()
        sock = self.transport.get_extra_info("socket")
        data, _ = await loop.sock_recvfrom(sock, size)
        filename = f"{self.config.imagepath}/{addr[0]}_image.jpg"
        with open(filename, "wb") as f:
            f.write(data)
        return filename

    def set_message_callback(self, callback):
        self.message_callback = callback

    def set_image_callback(self, callback):
        self.image_callback = callback

    async def send_known_to(self, ip, port):
        users = []
        for handle, (ip_, port_) in self.peers.items():
            users.append(f"{handle} {ip_} {port_}")
        message = "KNOWNUSERS " + ", ".join(users) + "\n"
        await self.send_slcp(message, ip, port)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
