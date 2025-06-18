import asyncio
import mimetypes
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
        self.progress_callback = None

    async def start_listener(self):
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
                    sender_ip, sender_port = addr[0], addr[1]
                    sender_handle = None
                    for handle, (ip, port) in self.peers.items():
                        if ip == sender_ip and port == sender_port:
                            sender_handle = handle
                            break
                    if not sender_handle:
                        for handle, (ip, _) in self.peers.items():
                            if ip == sender_ip:
                                sender_handle = f"{handle} (port {sender_port})"
                                break
                    sender_display = sender_handle if sender_handle else f"Unknown ({sender_ip}:{sender_port})"
                    if self.message_callback:
                        await self.message_callback(sender_display, msg)
                    else:
                        print(f"\n💬 Message from {sender_display}: {msg}")
                    if self.config.autoreply:
                        await self.send_message(sender_display, self.config.autoreply)

            elif parsed["type"] == "IMG":
                if parsed["to"] == self.config.handle:
                    print(f"[IMG] Peer {addr[0]} is sending an image via TCP...")

    async def send_slcp(self, line, ip, port):
        try:
            if self.transport:
                self.transport.sendto(line.encode(), (ip, port))
        except Exception as e:
            print(f"[Error] Failed to send to {ip}:{port}: {e}")

    async def send_broadcast(self, line):
        await self.send_slcp(line, "255.255.255.255", self.config.whoisport)

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
        if handle in self.peers:
            ip, port = self.peers[handle]
            msg = protocol.create_msg(handle, message)
            await self.send_slcp(msg, ip, port)
        else:
            print(f"[Error] Handle '{handle}' not connected")

    async def send_image(self, handle, filepath):
        if handle not in self.peers:
            print(f"[Error] No known peer with handle '{handle}'")
            return

        if not os.path.isfile(filepath):
            print(f"[Error] File '{filepath}' not found.")
            return

        try:
            with open(filepath, "rb") as f:
                img_bytes = f.read()
            size = len(img_bytes)

            mime_type, _ = mimetypes.guess_type(filepath)
            if not mime_type or not mime_type.startswith('image/'):
                print(f"[Error] File '{filepath}' is not a valid image.")
                return False

            print(f"[IMG] Preparing to send {size} bytes to {handle}")

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

                print(f"[IMG] Successfully sent image ({size} bytes) to {handle}")
                return True

            except asyncio.TimeoutError:
                print(f"[Error] Connection to {handle} timed out")
                return False
            except ConnectionRefusedError:
                print(f"[Error] Connection to {handle} refused")
                return False
            finally:
                tcp_socket.close()

        except Exception as e:
            print(f"[Error] Failed to send image: {e}")
            return False

    async def send_image_data(self, tcp_socket, img_bytes, handle):
        loop = asyncio.get_running_loop()
        total_size = len(img_bytes)
        sent = 0
        chunk_size = 8192  # 8KB chunks

        while sent < total_size:
            current_chunk_size = min(chunk_size, total_size - sent)
            chunk = img_bytes[sent:sent + current_chunk_size]

            await loop.sock_sendall(tcp_socket, chunk)
            sent += current_chunk_size

            if self.progress_callback:
                progress = (sent / total_size) * 100
                await self.progress_callback("send", handle, progress, sent, total_size)

            if sent < total_size:
                await asyncio.sleep(0.001)

    async def start_tcp_server(self):
        try:
            server = await asyncio.start_server(
                self.handle_tcp_connection,
                '0.0.0.0',
                self.config.port
            )
            print(f"[TCP] Server started on port {self.config.port}")

            async with server:
                await server.serve_forever()

        except Exception as e:
            print(f"[Error] Failed to start TCP server: {e}")

    async def handle_tcp_connection(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"[TCP] New connection from {addr}")

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
                    print(f"[IMG] Receiving {size} bytes from {handle}")
                    filename = await self.receive_image_data(reader, addr, size, handle)
                    if filename and self.image_callback:
                        if asyncio.iscoroutinefunction(self.image_callback):
                            await self.image_callback(handle, filename)
                        else:
                            self.image_callback(handle, filename)
                else:
                    print(f"[Error] Invalid IMG command format: {img_command}")
            else:
                print(f"[Error] Unknown TCP command: {img_command}")

        except asyncio.TimeoutError:
            print(f"[Error] TCP connection from {addr} timed out")
        except Exception as e:
            print(f"[Error] TCP connection error from {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def receive_image_data(self, reader, addr, size, sender_handle):
        try:
            img_data = b''
            received = 0

            while received < size:
                remaining = size - received
                chunk_size = min(8192, remaining)  # 8KB chunks

                try:
                    chunk = await asyncio.wait_for(
                        reader.read(chunk_size),
                        timeout=30.0  # 30 seconds timeout for each chunk
                    )

                    if not chunk:
                        print(f"[Error] Connection closed unexpectedly")
                        return None

                    img_data += chunk
                    received += len(chunk)

                    if self.progress_callback:
                        progress = (received / size) * 100
                        await self.progress_callback("receive", sender_handle, progress, received, size)

                except asyncio.TimeoutError:
                    print(f"[Error] Timeout while receiving image data")
                    return None

            timestamp = int(time.time())
            filename = os.path.join(
                self.config.imagepath,
                f"{addr[0]}_{timestamp}_{sender_handle}_image.jpg"
            )
            os.makedirs(self.config.imagepath, exist_ok=True)

            with open(filename, "wb") as f:
                f.write(img_data)
            print(f"[IMG] Successfully received and saved: {filename}")
            return filename

        except Exception as e:
            print(f"[Error] Failed to receive image: {e}")
            return None

    def set_progress_callback(self, callback):
        self.progress_callback = callback

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
