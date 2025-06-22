"""
@file main.py
@brief Hauptprogramm des P2P-Chat-Clients. Startet Discovery, Messenger, Interface (CLI).
"""

import asyncio
from Chat.config.config import Config
from Chat.network.messenger import Messenger
from Chat.discovery.discovery_service import DiscoveryService
from Chat.client.interface import Interface


async def main():
    """
    @brief Hauptfunktion des SLCP-Clients.

    Initialisiert alle Hauptkomponenten des Systems:
    - Lädt Konfiguration
    - Startet den Discovery-Dienst (UDP-basiert)
    - Initialisiert die Messenger-Komponente (SLCP)
    - Setzt Callback-Funktionen
    - Startet die Benutzeroberfläche (Kommandozeile)
    - Öffnet den UDP-Listener (für asynchrone Nachrichtenannahme)

    Ablauf:
    1. Lade Einstellungen wie Handle und Port aus TOML-Datei.
    2. Starte Discovery-Service für JOIN/LEAVE/WHO per Broadcast.
    3. Starte SLCP-Messenger für Nachrichten- und Bildversand.
    4. Starte CLI für Benutzereingaben.

    @return None
    """
    
    # 1. Konfiguration laden (z. B. aus slcp_config.toml)
    config = Config()

    # 2. Messenger-Komponente für SLCP-Protokoll initialisieren
    messenger = Messenger(config)

    # 3. Optional: Callback zur Anzeige des Dateiübertragungsfortschritts definieren
    def my_progress_callback(direction, peer, progress, sent, total):
        """
        @brief Zeigt den Fortschritt von Dateiübertragungen im Terminal.

        @param direction Richtung der Übertragung (SEND/RECV)
        @param peer Empfänger oder Sender (z. B. IP-Adresse)
        @param progress Fortschritt in Prozent (float)
        @param sent Bereits übertragene Bytes
        @param total Gesamtgröße der Datei
        """
        print(f"{direction} {progress:.1f}% ({sent}/{total} bytes) für {peer}")

    messenger.set_progress_callback(my_progress_callback)

    # 4. Discovery-Dienst starten (Broadcast JOIN + WHO → Peer-Erkennung)
    discovery = DiscoveryService("slcp_config.toml")
    discovery.start()

    # 5. Benutzeroberfläche (CLI) vorbereiten
    interface = Interface(config, messenger)

    # 6. Callbacks verknüpfen, damit Interface auf Ereignisse reagieren kann
    messenger.set_message_callback(interface.display_message)
    messenger.set_image_callback(interface.display_image_notice)
    messenger.set_knownusers_callback(interface.display_knownusers)

    # 7. Starte UDP-Listener für eingehende SLCP-Nachrichten
    await messenger.start_listener()

    # 8. Benutzeroberfläche starten → Befehlseingabe lesen und verarbeiten
    await interface.run()


if __name__ == "__main__":
    """
    @brief Einstiegspunkt des Programms.

    Startet das Eventloop mit der `main()` Funktion über asyncio.
    """
    asyncio.run(main())
