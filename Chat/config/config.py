import toml
import os

class Config:
    def __init__(self, path="slcp_config.toml"):
        self.path = path
        self.data = self.load()

        # Eingaben abfragen oder aus Datei nehmen
        self.handle = self.data.get("handle") or input("Benutzername (handle): ")
        self.port = int(self.data.get("port") or input("Port: "))
        self.whoisport = int(self.data.get("whoisport") or input("Whois-Port (z. B. 4000): "))
        self.autoreply = self.data.get("autoreply", "")
        self.imagepath = self.data.get("imagepath", "./images")

        # Kompatibilität: auch als `username` verfügbar machen
        self.username = self.handle  # ✅ wichtig!

        # alles zurückschreiben
        self.data["handle"] = self.handle
        self.data["port"] = self.port
        self.data["whoisport"] = self.whoisport
        self.data["autoreply"] = self.autoreply
        self.data["imagepath"] = self.imagepath
        self.save()


    def load(self):
        if os.path.exists(self.path):
            return toml.load(self.path)
        return {}

    def save(self):
        with open(self.path, "w") as f:
            toml.dump(self.data, f)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
