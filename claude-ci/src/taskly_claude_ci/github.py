import secrets


def multiline_output(name: str, value: str) -> str:
    delimiter = f"EOF_{secrets.token_hex(16)}"
    return f"{name}<<{delimiter}\n{value.rstrip()}\n{delimiter}"


def output(name: str, value: str) -> str:
    return f"{name}={value}"
