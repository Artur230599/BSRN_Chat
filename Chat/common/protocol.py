def parse_message(raw):
    parts = raw.strip().split(" ")
    command = parts[0]
    params = parts[1:]
    return command, params


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
