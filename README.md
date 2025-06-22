# BSRN-Chat – Peer-to-Peer Chat mit Text- und Bildübertragung

## Überblick

Dieses Projekt ist eine Peer-to-Peer-Chat-Anwendung in Python für das Modul Betriebsystem und Rechnernetz.  
Es unterstützt die automatische Discovery von Peers im lokalen Netzwerk, das Versenden und Empfangen von Textnachrichten sowie Bildern.  
Bedient wird das Programm über eine intuitive CLI (Command Line Interface).  
Die technische und architektonische Dokumentation findet sich als PDF unter dem Namen DOKUMENTATION oder im Ordner `/latex/refman.pdf`.

---

## Hauptfunktionen

- **Discovery-Service:** Findet automatisch andere Benutzer im LAN (UDP-Broadcast, JOIN/WHO/KNOWNUSERS)
- **Textnachrichten:** Senden/Empfangen per UDP/TCP, mit Autoreply-Funktion
- **Bildübertragung:** Versenden von Bildern als Datei-Stream (TCP, Chunking, Format-Check)
- **CLI-Befehle:** `/join`, `/leave`, `/who`, `/msg`, `/img`, `/quit`
- **Doxygen-Dokumentation:** API-Doku automatisch generiert aus dem Code

---

## Installation & Setup

1. **Repository klonen:**
    ```bash
    git clone https://github.com/Artur230599/BSRN_Chat.git
    cd BSRN_Chat
    ```

2. **Python-Abhängigkeiten installieren:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Konfiguration prüfen/anpassen:**  
   Die Datei `slcp_config.toml` im Projektordner enthält alle wichtigen Einstellungen (Benutzername, Ports, Autoreply-Text, Bildpfad).

---

## Programmstart & Bedienung

- **Programm starten:**
    ```bash
    python3 -m Chat.main
    ```

- **Wichtige CLI-Befehle:**
    - `/join` – Chat beitreten
    - `/msg <handle> <text>` – Nachricht senden
    - `/img <handle> <pfad>` – Bild senden
    - `/who` – Aktive Benutzer anzeigen
    - `/leave` – Chat verlassen
    - `/quit` – Programm beenden

- **Beispiel:**
    ```
    /join
    /msg Aysha Hallo!
    /img Aysha bilder/cat.png
    /who
    /leave
    /quit
    ```

---

## Architektur

Ein Überblick der Software-Architektur (siehe auch Dokumentation):

```text
┌─────────────┐      ┌─────────────┐      ┌───────────────┐
│  Interface  │◄────►│  Messenger  │◄───► │ DiscoverySrv  │
│  (CLI)      │      │  (Netzwerk) │      │ (UDP-Service) │
└─────────────┘      └─────────────┘      └───────────────┘
       │                    │
       ▼                    ▼
  Senden/Empf.         Text/Bilder
 Benutzer-Eingabe        UDP/TCP
```

---

## Autoren

- Aysha Aryubi  
- Nhu Ngoc Le
- Artur Gubarkov
