import toml  # Für das Einlesen/Schreiben der Konfigurationsdatei
import os    # Für Datei- und Pfadoperationen

class Config:
    """
    @class Config
    @brief Verwaltet die Konfiguration des Chat-Clients.

    Diese Klasse lädt, speichert und verwaltet Benutzereinstellungen aus einer TOML-Datei.
    Falls Werte fehlen (z. B. Benutzername oder Port), werden sie beim ersten Start interaktiv abgefragt.
    """

    def __init__(self, path="slcp_config.toml"):
        """
        @brief Initialisiert eine neue Konfigurationsinstanz.

        - Liest Konfiguration aus Datei (sofern vorhanden).
        - Fragt fehlende Parameter interaktiv ab.
        - Erstellt Standardverzeichnisse bei Bedarf.

        @param path Dateipfad zur TOML-Konfigurationsdatei (Standard: slcp_config.toml)
        """
        self.path = path
        self.data = self.load()

        # Benutzername (Handle) laden oder abfragen
        self.handle = self.data.get("handle")
        if not self.handle:
            self.handle = input("Benutzername (handle): ")
            self.data["handle"] = self.handle

        # Port laden oder abfragen
        self.port = int(self.data.get("port") or input("Port: "))
        self.data["port"] = self.port

        # Whois-Port laden oder abfragen
        self.whoisport = int(self.data.get("whoisport") or input("Whois-Port (z. B. 4000): "))
        self.data["whoisport"] = self.whoisport

        # Automatische Antwort (optional)
        self.autoreply = self.data.get("autoreply", "")

        # Pfad für empfangene Bilder vorbereiten
        self.imagepath = self._setup_imagepath()

        # Konfiguration speichern, falls sie neu ist oder aktualisiert wurde
        if not os.path.exists(self.path) or "handle" not in toml.load(self.path):
            self.save()

    def _setup_imagepath(self):
        """
        @brief Bereitet den Ordnerpfad für empfangene Bilder vor.

        - Nutzt Standardpfad, wenn nicht angegeben.
        - Erstellt das Verzeichnis bei Bedarf.

        @return Absoluter Pfad zum Bildspeicherordner (z. B. ~/slcp_images)
        """
        raw_path = self.data.get("imagepath", "~/slcp_images")
        normalized_path = os.path.abspath(os.path.expanduser(raw_path))
        os.makedirs(normalized_path, exist_ok=True)
        self.data["imagepath"] = normalized_path
        return normalized_path

    def load(self):
        """
        @brief Lädt die Konfiguration aus der TOML-Datei.

        @return Dictionary mit den geladenen Konfigurationswerten.
        """
        if os.path.exists(self.path):
            return toml.load(self.path)
        return {}

    def save(self):
        """
        @brief Speichert die aktuelle Konfiguration zurück in die TOML-Datei.
        """
        with open(self.path, "w") as f:
            toml.dump(self.data, f)
