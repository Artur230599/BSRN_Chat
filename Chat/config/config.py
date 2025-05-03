import toml
import os

class Config:
    def __init__(self, path="slcp_config.toml"):
        self.path = path
        self.data = self.load()

        # Attribute direkt verfügbar machen
        self.username = self.data.get("username") or input("Benutzername eingeben: ")
        self.port = int(self.data.get("port") or input("Port eingeben: "))

        # Optional speichern, wenn neu eingegeben
        self.data["username"] = self.username
        self.data["port"] = self.port
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
