# network/messenger.py

import asyncio
import json
import socket
from asyncio import DatagramProtocol
from config.config import Config

class Messenger(DatagramProtocol):
    def __init__(self, config: Config):
        self.config = config
        self.peers = {}  # username -> (ip, port)
        self.transport = None

    async def start_listener(self):
        loop = asyncio.get_running_loop()

        # UDP Socket für Broadcast vorbereiten
        listen = lambda: self
        self.transport, _ = await loop.create_datagram_endpoint(
            listen,
            local_addr=("0.0.0.0", self.config.port),
            family=socket.AF_INET,
            proto=socket.IPPROTO_UDP,
            allow_broadcast=True
        )
        print(f"[Messenger] Listening on port {self.config.port}")

        # Sende JOIN direkt nach Start
        await asyncio.sleep(1)
        await self.broadcast_join()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = json.loads(data.decode())
        asyncio.create_task(self.handle_message(message, addr))

    async def handle_message(self, msg, addr):
        msg_type = msg.get("type")
        sender_username = msg.get("username")

        if sender_username == self.config.username:
            return  # Eigene Nachrichten ignorieren

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

    async def send_message(self, message: dict, ip: str, port: int):
        if self.transport:
            data = json.dumps(message).encode()
            self.transport.sendto(data, (ip, port))

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
