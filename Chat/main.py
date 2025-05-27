import asyncio
from config.config import Config
from network.messenger import Messenger
from discovery.discovery_service import DiscoveryService
from client.interface import Interface


async def main():
    config = Config()
    discovery = DiscoveryService(config)
    messenger = Messenger(config)
    interface = Interface(config, messenger)

    loop = asyncio.get_running_loop()

    # Discovery-Dienst separat starten
    loop.run_in_executor(None, discovery.start)

    # Messenger Listener starten
    try:
        await messenger.start_listener()
        await interface.run()
    except KeyboardInterrupt:
        print("Stopping discovery service...")
        discovery.stop()


if __name__ == "__main__":
    asyncio.run(main())

