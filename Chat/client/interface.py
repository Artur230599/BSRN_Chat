import asyncio
import os
from colorama import Fore, Style, init

class Interface:
    def __init__(self, config, messenger):
        self.config = config
        self.messenger = messenger
        init()

    async def run(self):
        print(f"{Fore.GREEN}🟢 Willkommen im SLCP-Chat, {self.config.handle}!{Style.RESET_ALL}")
        print(f"""{Fore.CYAN}
Verfügbare Befehle:
  {Fore.YELLOW}/join{Fore.CYAN} - Dem Chat beitreten
  {Fore.YELLOW}/leave{Fore.CYAN} - Chat verlassen
  {Fore.YELLOW}/who{Fore.CYAN} - Aktive Benutzer anzeigen
  {Fore.YELLOW}/msg <handle> <text>{Fore.CYAN} - Nachricht senden
  {Fore.YELLOW}/img <handle> <pfad>{Fore.CYAN} - Bild senden
  {Fore.YELLOW}/quit{Fore.CYAN} - Chat beenden
{Style.RESET_ALL}""")

        while True:
            try:
                command = await asyncio.to_thread(input, f"{Fore.MAGENTA}>> {Style.RESET_ALL}")
                command = command.strip()

                if command == "/join":
                    await self.messenger.send_join()
                    print(f"{Fore.GREEN}✅ Du bist dem Chat beigetreten!{Style.RESET_ALL}")

                elif command == "/leave":
                    await self.messenger.send_leave()
                    print(f"{Fore.YELLOW}🟡 Du hast den Chat verlassen.{Style.RESET_ALL}")

                elif command.startswith("/who"):
                    await self.messenger.send_who()

                elif command.startswith("/msg"):
                    parts = command.split(" ", 2)
                    if len(parts) < 3:
                        print(f"{Fore.RED}❌ Usage: /msg <handle> <text>{Style.RESET_ALL}")
                    else:
                        await self.messenger.send_message(parts[1], parts[2])

                elif command.startswith("/img"):
                    parts = command.split(" ", 2)
                    if len(parts) < 3:
                        print(f"{Fore.RED}❌ Usage: /img <handle> <pfad>{Style.RESET_ALL}")
                    else:
                        handle, pfad = parts[1], parts[2]
                        if not os.path.isfile(pfad):
                            print(f"{Fore.RED}❌ Datei nicht gefunden: {pfad}{Style.RESET_ALL}")
                        elif not pfad.lower().endswith(('.jpg', '.jpeg', '.png')):
                            print(f"{Fore.RED}❌ Ungültiges Bildformat!{Style.RESET_ALL}")
                        else:
                            success = await self.messenger.send_image(handle, pfad)
                            if success:
                                print(f"{Fore.GREEN}🖼️ Bild an {handle} gesendet!{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.RED}❌ Bildversand fehlgeschlagen!{Style.RESET_ALL}")

                elif command == "/quit":
                    await self.messenger.send_leave()
                    print(f"{Fore.RED}🔴 Chat wird beendet...{Style.RESET_ALL}")
                    break

                else:
                    print(f"{Fore.RED}❌ Unbekannter Befehl.{Style.RESET_ALL}")

            except Exception as e:
                print(f"{Fore.RED}⚠️ Fehler: {e}{Style.RESET_ALL}")

    async def display_message(self, sender_display, message):
        print(f"\n{Fore.BLUE}💬 {sender_display}: {Fore.RESET}{message}")

    async def display_image_notice(self, sender, filename):
        print(f"\n{Fore.GREEN}🖼️ Bild von {sender}: {Fore.YELLOW}{filename}{Style.RESET_ALL}")

    async def display_knownusers(self, user_list):
        print(f"\n{Fore.CYAN}🌐 Aktive Benutzer:{Style.RESET_ALL}")
        seen = set()
        for handle, ip, port in user_list:
            if handle not in seen:
                print(f"  {Fore.YELLOW}👉 {handle:8}{Fore.RESET} an {ip}:{port}")
                seen.add(handle)
