import asyncio
import os


class Interface:
    def __init__(self, config, messenger):
        self.config = config
        self.messenger = messenger

    async def run(self):
        print(f"🟢 Willkommen im SLCP-Chat, {self.config.handle}!")
        print("Verfügbare Befehle: /join, /leave, /who, /msg <handle> <text>, /img <handle> <pfad>, /quit")

        while True:
            try:
                command = await asyncio.to_thread(input, ">> ")
                command = command.strip()

                if command == "/join":
                    await self.messenger.send_join()

                elif command == "/leave":
                    await self.messenger.send_leave()

                elif command.startswith("/who"):
                    await self.messenger.send_who()

                elif command.startswith("/msg"):
                    parts = command.split(" ", 2)
                    if len(parts) < 3:
                        print("❌ Usage: /msg <handle> <text>")
                    else:
                        await self.messenger.send_message(parts[1], parts[2])

                elif command.startswith("/img"):
                    parts = command.split(" ", 2)
                    if len(parts) < 3:
                        print("❌ Usage: /img <handle> <pfad>")
                    else:
                        handle, pfad = parts[1], parts[2]
                        if not os.path.isfile(pfad):
                            print(f"❌ Datei nicht gefunden: {pfad}")
                        elif not pfad.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                            print(f"❌ '{pfad}' ist keine Bilddatei.")
                        else:
                            result = await self.messenger.send_image(handle, pfad)
                            if result:
                                print(f"🖼️ Bild wird gesendet an {handle}...")
                            else:
                                print("❌ Bildversand fehlgeschlagen!")

                elif command == "/quit":
                    await self.messenger.send_leave()
                    print("🔚 Chat wird beendet...")
                    break

                else:
                    print("❓ Unbekannter Befehl.")

            except Exception as e:
                print(f"⚠️ Fehler in Interface: {e}")

    async def display_message(self, sender_display, message):
        print(f"\n💬 Nachricht von {sender_display}: {message}")

    async def display_image_notice(self, sender, filename):
        print(f"\n🖼️ Bild von {sender} empfangen: {filename}")

    async def display_knownusers(self, user_list):
        print("\n🌐 Aktive Benutzer:")
        for handle, ip, port in user_list:
            print(f"  👉 {handle:8} an {ip}:{port}")

