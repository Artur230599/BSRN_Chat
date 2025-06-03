import multiprocessing
import toml
from discovery import run_discovery_service
from network import run_network_service
from ui import run_ui

def load_config():
with open("config.toml", "r") as f:
return toml.load(f)

def main():
config = load_config()
to_network = multiprocessing.Queue()
to_ui = multiprocessing.Queue()
to_discovery = multiprocessing.Queue()

discovery_process = multiprocessing.Process(
target=run_discovery_service,
args=(config, to_discovery, to_ui)
)

network_process = multiprocessing.Process(
target=run_network_service,
args=(config, to_network, to_ui)
)

ui_process = multiprocessing.Process(
target=run_ui,
args=(config, to_ui, to_network, to_discovery)
)

discovery_process.start()
network_process.start()
ui_process.start()

ui_process.join()
discovery_process.terminate()
network_process.terminate()

if __name__ == "__main__":
main()