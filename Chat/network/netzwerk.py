import asyncio
import json
import socket
import os
from asyncio import DatagramProtocol

class Messenger(DatagramProtocol):
    def __init__(self, config):
        self.config = config
        self.peers = {}  # username -> (ip, port)
        self.transport = None
        self.expecting_image = None

    async def start_listener(self):
        loop = asyncio.get_running_loop()
        listen = lambda: self
        self.transport, _ = await loop.create_datagram_endpoint(
            listen,
            local_addr=("0.0.0.0", self.config.port),
            family=socket.AF_INET,
            proto=socket.IPPROTO_UDP
        )
        print(f"[Messenger] Listening on port {self.config.port}")
        await asyncio.sleep(1)
        await self.broadcast_join()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        try:
            text = data.decode()
            msg = json.loads(text)
            asyncio.create_task(self.handle_message(msg, addr))
        except (UnicodeDecodeError, json.JSONDecodeError):
            if self.expecting_image and self.expecting_image["ip"] == addr[0]:
                expected_size = self.expecting_image["size"]
                if len(data) == expected_size:
                    filename = f"/mnt/data/received_from_{self.expecting_image['from']}.bin"
                    with open(filename, "wb") as f:
                        f.write(data)
                    print(f"[IMG] Image saved as: {filename}")
                    self.expecting_image = None
                else:
                    print(f"[IMG] Received unexpected image size: {len(data)} (expected {expected_size})")
            else:
                print("[IMG] Received unknown binary data")

    async def handle_message(self, msg, addr):
        msg_type = msg.get("type")
        sender_username = msg.get("username")

        if sender_username == self.config.username:
            return

        if msg_type == "JOIN":
            self.peers[sender_username] = (addr[0], msg["port"])
            print(f"[JOIN] {sender_username} joined from {addr[0]}:{msg['port']}")

        elif msg_type == "LEAVE":
            if sender_username in self.peers:
                del self.peers[sender_username]
                print(f"[LEAVE] {sender_username} has left")

        elif msg_type == "WHOIS":
            if msg["username"] == self.config.username:
                response = {
                    "type": "WHOIS_RESPONSE",
                    "username": self.config.username,
                    "port": self.config.port
                }
                await self.send_message(response, addr[0], msg["port"])

        elif msg_type == "WHOIS_RESPONSE":
            self.peers[sender_username] = (addr[0], msg["port"])
            print(f"[WHOIS] {sender_username} is at {addr[0]}:{msg['port']}")

        elif msg_type == "MSG" and msg.get("to") == self.config.username:
            print(f"[MSG] From {sender_username}: {msg.get('message')}")

        elif msg_type == "IMG" and msg.get("to") == self.config.username:
            self.expecting_image = {
                "from": sender_username,
                "size": msg["size"],
                "ip": addr[0],
                "port": addr[1]
            }
            print(f"[IMG] Incoming image from {sender_username} ({msg['size']} bytes)")

    async def send_message(self, message: dict, ip: str, port: int):
        if self.transport:
            data = json.dumps(message).encode()
            self.transport.sendto(data, (ip, port))

    async def send_chat_message(self, to_username: str, text: str):
        if to_username not in self.peers:
            print(f"[MSG] Unknown user '{to_username}'. Try WHOIS first.")
            return

        ip, port = self.peers[to_username]
        message = {
            "type": "MSG",
            "username": self.config.username,
            "to": to_username,
            "message": text
        }
        await self.send_message(message, ip, port)

    async def send_image(self, to_username: str, image_path: str):
        if to_username not in self.peers:
            print(f"[IMG] Unknown user '{to_username}'. Try WHOIS first.")
            return

        ip, port = self.peers[to_username]
        try:
            size = os.path.getsize(image_path)
            img_header = {
                "type": "IMG",
                "username": self.config.username,
                "to": to_username,
                "size": size
            }
            await self.send_message(img_header, ip, port)

            with open(image_path, "rb") as f:
                data = f.read()
                self.transport.sendto(data, (ip, port))
                print(f"[IMG] Sent image to {to_username} ({size} bytes)")

        except Exception as e:
            print(f"[IMG] Failed to send: {e}")

    async def broadcast_join(self):
        message = {
            "type": "JOIN",
            "username": self.config.username,
            "port": self.config.port
        }
        self.send_broadcast(message)

    async def broadcast_leave(self):
        message = {
            "type": "LEAVE",
            "username": self.config.username,
            "port": self.config.port
        }
        self.send_broadcast(message)

    def send_broadcast(self, message: dict):
        data = json.dumps(message).encode()
        if self.transport:
            self.transport.sendto(data, ("255.255.255.255", self.config.port))

    async def send_whois_request(self, username: str):
        message = {
            "type": "WHOIS",
            "username": username,
            "port": self.config.port
        }
        self.send_broadcast(message)
