import asyncio
from Chat.config.config import Config
from Chat.network.messenger import Messenger
from Chat.discovery.discovery_service import DiscoveryService
from Chat.client.interface import Interface


async def main():
    # Konfiguration laden
    config = Config()

    # Messenger initialisieren
    messenger = Messenger(config)

    # Progress Callback setzen
    def my_progress_callback(direction, peer, progress, sent, total):
        print(f"{direction} {progress:.1f}% ({sent}/{total} bytes) für {peer}")

    messenger.set_progress_callback(my_progress_callback)

    # Discovery starten
    discovery = DiscoveryService("slcp_config.toml")
    discovery.start()

    # Interface vorbereiten
    interface = Interface(config, messenger)

    # Callbacks setzen
    messenger.set_message_callback(interface.display_message)
    messenger.set_image_callback(interface.display_image_notice)
    messenger.set_knownusers_callback(interface.display_knownusers)

    # UDP-Listener für SLCP starten
    await messenger.start_listener()

    # Benutzeroberfläche starten (Eingabeaufforderung)
    await interface.run()


if __name__ == "__main__":
    asyncio.run(main())