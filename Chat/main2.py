import asyncio
import threading
from Chat.config.config import Config
from Chat.network.messenger import Messenger
from Chat.discovery.discovery_service import DiscoveryService
from Chat.client.gui import ChatGUI

def start_gui(config, messenger):
    gui = ChatGUI(config, messenger)
    gui.start()  # <-- mainloop() runs in main thread

async def start_backend(config, messenger):
    # Progress Callback
    def my_progress_callback(direction, peer, progress, sent, total):
        print(f"{direction} {progress:.1f}% ({sent}/{total} bytes) for {peer}")
    messenger.set_progress_callback(my_progress_callback)

    # Discovery
    discovery = DiscoveryService("slcp_config.toml")
    discovery.start()
    await messenger.start_listener()
    await asyncio.Event().wait()

def main():
    config = Config()
    messenger = Messenger(config)

    backend_thread = threading.Thread(target=lambda: asyncio.run(start_backend(config, messenger)), daemon=True)
    backend_thread.start()

    start_gui(config, messenger)

if __name__ == "__main__":
    main()
