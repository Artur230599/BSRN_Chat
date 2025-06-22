"""
@file interface.py
@brief Kommandozeilen-Benutzeroberfläche (CLI) für den SLCP-Chat-Client.
Stellt Eingabe, Ausgabe und Nutzerinteraktion über Terminal bereit.
"""

import asyncio
import os
from colorama import Fore, Style, init

class Interface:
    """
    @class Interface
    @brief CLI-basierte Benutzeroberfläche für den SLCP-Chat-Client.

    Diese Klasse stellt die Interaktion des Nutzers mit dem SLCP-Chat über ein Konsoleninterface bereit.
    Sie verwaltet alle Benutzereingaben, interpretiert SLCP-Befehle wie /join, /leave, /msg usw.
    und leitet sie asynchron an die Messenger-Komponente zur Verarbeitung weiter.

    Zusätzlich wird die farbliche Konsolenausgabe mit dem Modul `colorama` unterstützt,
    um Statusnachrichten und Befehle übersichtlicher darzustellen.
    """

    def __init__(self, config, messenger):
        """
        @brief Konstruktor der Interface-Klasse.

        Initialisiert das Interface mit Konfigurationsdaten und der Messenger-Instanz
        zur Netzwerkkommunikation.

        @param config Ein Konfigurationsobjekt mit Nutzername, Port, Autoreply etc.
        @param messenger Eine Messenger-Instanz, die SLCP-Nachrichten verarbeitet und verschickt
        """
        self.config = config
        self.messenger = messenger
        init()  # Initialisiere colorama (Farben für Terminalausgabe)

    async def run(self):
        """
        @brief Startet die Haupt-Eingabeschleife für den Nutzer.

        Die Methode zeigt verfügbare Befehle an, liest Eingaben von der Konsole
        (z. B. /join, /msg, /img), prüft diese auf Gültigkeit und ruft entsprechende
        Messenger-Methoden zur Verarbeitung auf. Sie läuft bis der Befehl /quit ausgeführt wird.
        """
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
                # Eingabe vom Nutzer in einem eigenen Thread lesen (blockierend)
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
                            print(f"{Fore.RED}❌ Ungültiges Bildformat! (.jpg/.png erlaubt){Style.RESET_ALL}")
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
        """
        @brief Zeigt eine empfangene Textnachricht in der Konsole an.

        Wird vom Messenger aufgerufen, wenn eine neue Nachricht vom Netzwerk empfangen wurde.

        @param sender_display Der Anzeigename oder die IP-Adresse des Absenders
        @param message Die empfangene Textnachricht
        """
        print(f"\n{Fore.BLUE}💬 {sender_display}: {Fore.RESET}{message}")

    async def display_image_notice(self, sender, filename):
        """
        @brief Zeigt eine Benachrichtigung über ein empfangenes Bild an.

        Diese Methode wird als Callback bei erfolgreichem Empfang eines Bildes aufgerufen.

        @param sender Handle oder IP des Absenders
        @param filename Pfad zur lokal gespeicherten Bilddatei
        """
        print(f"\n{Fore.GREEN}🖼️ Bild von {sender}: {Fore.YELLOW}{filename}{Style.RESET_ALL}")

    async def display_knownusers(self, user_list):
        """
        @brief Gibt alle bekannten/erkannten Nutzer formatiert auf der Konsole aus.

        Diese Methode wird nach Empfang einer KNOWNUSERS-Nachricht genutzt, um
        alle bekannten Peers in der Benutzeroberfläche anzuzeigen.

        @param user_list Liste von Tupeln: (handle, ip, port)
        """
        print(f"\n{Fore.CYAN}🌐 Aktive Benutzer:{Style.RESET_ALL}")
        seen = set()
        for handle, ip, port in user_list:
            if handle not in seen:
                print(f"  {Fore.YELLOW}👉 {handle:8}{Fore.RESET} an {ip}:{port}")
                seen.add(handle)
