def parse_slcp(line):
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
                            "port": int(user_parts[2])})
            return {"type": "KNOWNUSERS", "users": users}

    except (ValueError, IndexError) as e:
        print(f"Parse error: {e} for line: {line}")

    return {"type": "UNKNOWN", "raw": line}


def create_join(handle, port):
    return f"JOIN {handle} {port}\n"


def create_leave(handle):
    return f"LEAVE {handle}\n"


def create_msg(target, text):
    return f'MSG {target} "{text}"\n'


def create_img(target, size):
    return f"IMG {target} {size}\n"


def create_who():
    return f"WHO\n"


def create_knownusers(users):
    user_entries = []
    for user in users:
        user_entries.append(f"{user['handle']} {user['ip']} {user['port']}")
    return f"KNOWNUSERS {', '.join(user_entries)}\n"
