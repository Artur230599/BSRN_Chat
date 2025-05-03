import socket
import os
import platform
from common.protocol import parse_message, create_iam

class DiscoveryService:
    def __init__(self, config):
        self.config = config
        self.handle = config.get("handle")
        self.port = config.get("port")
        self.whoisport = config.get("whoisport", 4000)
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", self.whoisport))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def start(self):
        print("[Discovery] Discovery-Dienst läuft...")

        # Plattformunabhängiges PID-File:
        if platform.system() == "Windows":
            pid_file = f"slcp.pid"   # Windows einfach im Projektordner
        else:
            pid_file = f"/run/user/{os.getuid()}/slcp.pid"  # Linux/Unix

        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        try:
            while self.running:
                data, addr = self.sock.recvfrom(512)
                msg = data.decode("utf-8").strip()
                command, params = parse_message(msg)

                if command == "WHOIS" and params[0] == self.handle:
                    response = create_iam(self.handle, addr[0], self.port)
                    self.sock.sendto(response.encode("utf-8"), addr)
                    print(f"[Discovery] WHOIS erhalten → IAM gesendet an {addr}")
        except KeyboardInterrupt:
            print("\n[Discovery] Discovery-Dienst gestoppt.")
        finally:
            if os.path.exists(pid_file):
                os.remove(pid_file)

    def stop(self):
        self.running = False
        self.sock.close()
