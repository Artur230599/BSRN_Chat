##
# @file protocol.py
# @brief Enthält Funktionen zum Parsen und Erzeugen von SLCP-Protokollnachrichten.
#
# Diese Datei stellt das Kommunikationsprotokoll bereit, das vom Messenger und Discovery-Service
# verwendet wird, um Text- und Bildnachrichten sowie Netzwerkanfragen zu senden und zu empfangen.

def parse_slcp(line):
    """
    @brief Parst eine SLCP-Zeile (Simple Local Chat Protocol) in ein Dictionary.

    Unterstützte Befehle:
    - JOIN <handle> <port>
    - LEAVE <handle>
    - WHO
    - MSG <to> <message>
    - IMG <to> <size>
    - KNOWNUSERS <handle1> <ip1> <port1>, ...

    @param line SLCP-Zeile als String
    @return Dictionary mit Schlüssel "type" und weiteren Feldern je nach Befehl
    """
    parts = line.strip().split(" ")
    if not parts:
        return {}

    cmd = parts[0]
    try:
        if cmd == "JOIN" and len(parts) == 3:
            return {"type": "JOIN", "handle": parts[1], "port": int(parts[2])}

        elif cmd == "LEAVE" and len(parts) == 2:
            return {"type": "LEAVE", "handle": parts[1]}

        elif cmd == "WHO" and len(parts) == 1:
            return {"type": "WHO"}

        elif cmd == "MSG" and len(parts) >= 3:
            to = parts[1]
            text = " ".join(parts[2:]).strip('"')
            return {"type": "MSG", "to": to, "message": text}

        elif cmd == "IMG" and len(parts) == 3:
            return {"type": "IMG", "to": parts[1], "size": int(parts[2])}

        elif cmd == "KNOWNUSERS" and len(parts) >= 1:
            users = []
            user_data = ' '.join(parts[1:]).split(',')
            for entry in user_data:
                entry = entry.strip()
                if entry:
                    user_parts = entry.split()
                    if len(user_parts) == 3:
                        users.append({
                            "handle": user_parts[0],
                            "ip": user_parts[1],
                            "port": int(user_parts[2])
                        })
            return {"type": "KNOWNUSERS", "users": users}

    except (ValueError, IndexError) as e:
        print(f"Parse error: {e} for line: {line}")

    return {"type": "UNKNOWN", "raw": line}


def create_join(handle, port):
    """
    @brief Erstellt eine JOIN-Nachricht.

    @param handle Benutzername
    @param port Portnummer
    @return SLCP-konforme JOIN-Zeile
    """
    return f"JOIN {handle} {port}\n"


def create_leave(handle):
    """
    @brief Erstellt eine LEAVE-Nachricht.

    @param handle Benutzername
    @return SLCP-konforme LEAVE-Zeile
    """
    return f"LEAVE {handle}\n"


def create_msg(target, text):
    """
    @brief Erstellt eine MSG-Nachricht zum Senden eines Textes.

    @param target Empfänger-Handle
    @param text Nachrichtentext
    @return SLCP-konforme MSG-Zeile
    """
    return f'MSG {target} "{text}"\n'


def create_img(target, size):
    """
    @brief Erstellt eine IMG-Nachricht zum Senden von Bilddaten.

    @param target Empfänger-Handle
    @param size Größe des Bildes in Bytes
    @return SLCP-konforme IMG-Zeile
    """
    return f"IMG {target} {size}\n"


def create_who():
    """
    @brief Erstellt eine WHO-Broadcast-Nachricht zur Abfrage aller bekannten Nutzer.

    @return SLCP-konforme WHO-Zeile
    """
    return f"WHO\n"


def create_knownusers(users):
    """
    @brief Erstellt eine KNOWNUSERS-Nachricht mit Liste aller bekannten Peers.

    @param users Liste von Dictionaries mit Schlüsseln 'handle', 'ip', 'port'
    @return SLCP-konforme KNOWNUSERS-Zeile
    """
    user_entries = []
    for user in users:
        user_entries.append(f"{user['handle']} {user['ip']} {user['port']}")
    return f"KNOWNUSERS {', '.join(user_entries)}\n"
