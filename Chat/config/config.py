import toml
import os

class Config:
    def __init__(self, path="slcp_config.toml"):
        self.path = path
        self.data = self.load()

        # Hole handle/port — aus Datei ODER frage ab, wenn nicht gesetzt
        self.handle = self.data.get("handle")
        if not self.handle:
            self.handle = input("Benutzername (handle): ")
            self.data["handle"] = self.handle

        self.port = int(self.data.get("port") or input("Port: "))
        self.data["port"] = self.port

        self.whoisport = int(self.data.get("whoisport") or input("Whois-Port (z. B. 4000): "))
        self.data["whoisport"] = self.whoisport

        self.autoreply = self.data.get("autoreply", "")
        self.imagepath = self._setup_imagepath()

        # Nur speichern, wenn noch nicht vorhanden – nicht jedes Mal!
        if not os.path.exists(self.path) or "handle" not in toml.load(self.path):
            self.save()

    def _setup_imagepath(self):
        raw_path = self.data.get("imagepath", "~/slcp_images")

        normalized_path = os.path.abspath(os.path.expanduser(raw_path))

        os.makedirs(normalized_path, exist_ok=True)

        self.data["imagepath"] = normalized_path
        return normalized_path

    def load(self):
        if os.path.exists(self.path):
            return toml.load(self.path)
        return {}

    def save(self):
        with open(self.path, "w") as f:
            toml.dump(self.data, f)
