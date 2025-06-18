def parse_slcp(line):
    parts = line.strip().split(" ")
    if not parts:
        return {}

    cmd = parts[0]

    if cmd == "JOIN" and len(parts) == 3:
        return {"type": "JOIN", "handle": parts[1], "port": int(parts[2])}

    elif cmd == "LEAVE" and len(parts) == 2:
        return {"type": "LEAVE", "handle": parts[1]}

    elif cmd == "WHO" and len(parts) == 2:
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

    return {"type": "UNKNOWN", "raw": line}


def create_join(handle, port):
    return f"JOIN {handle} {port}\n"


def create_leave(handle):
    return f"LEAVE {handle}\n"


def create_msg(target, text):
    return f'MSG {target} "{text}"\n'


def create_img(target, size):
    return f"IMG {target} {size}\n"


def create_whois(handle):
    return f"WHOIS {handle}\n"


def create_iam(handle, ip, port):
    return f"IAM {handle} {ip} {port}\n"
