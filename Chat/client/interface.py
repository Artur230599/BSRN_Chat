# client/interface.py

import asyncio

class Interface:
    def __init__(self, config, messenger):
        self.config = config
        self.messenger = messenger

    async def run(self):
        print("Welcome to the chat.")
        print("Commands: whois <username>, join, leave, quit")

        while True:
            command = input(">> ").strip()

            if command == "/join":
                await self.messenger.broadcast_join()

            elif command == "/leave":
                await self.messenger.broadcast_leave()

            elif command.startswith("/whois"):
                parts = command.split()
                if len(parts) == 2:
                    username = parts[1]
                    await self.messenger.send_whois_request(username)
                else:
                    print("Usage: /whois <username>")

            elif command == "/quit":
                print("Exiting...")
                break

            else:
                print("Unknown command.")
