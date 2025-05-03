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
    await messenger.start_listener()

    # CLI starten
    await interface.run()


if __name__ == "__main__":
    asyncio.run(main())

