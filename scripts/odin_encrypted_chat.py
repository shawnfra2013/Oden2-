"""Decrypt paired browser messages only on Odin. Git carries ciphertext."""
import base64
import os
import re
import secrets
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path.home() / ".config/odin-encrypted-chat"


def b64(data):
    return base64.b64encode(data).decode("ascii")


def pairing_key():
    with os.fdopen(os.open(CONFIG / "browser.key", os.O_RDONLY | os.O_NOFOLLOW), "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Invalid pairing key permissions")
        key = handle.read(33)
    if len(key) != 32:
        raise ValueError("Invalid pairing key")
    return key


def reply(request):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not re.fullmatch("[0-9a-f]{32}", request["id"]):
        raise ValueError("Invalid request ID")
    if str(ROOT / "stage5") not in sys.path:
        sys.path.insert(0, str(ROOT / "stage5"))
    from local_adapter import ask_local
    from offline_profile import activate
    activate(os.environ)

    data = base64.b64decode(request["sealed"], validate=True)
    if not 28 < len(data) <= 12029:
        raise ValueError("Invalid encrypted message size")
    from cryptography.exceptions import InvalidTag

    cipher = AESGCM(pairing_key())
    prefix = ("odin-chat-v1/" + request["id"] + "/").encode()
    try:
        question = cipher.decrypt(data[:12], data[12:], prefix + b"question").decode()
    except InvalidTag as exc:
        raise ValueError("Unpaired message") from exc
    answer = ask_local(question)
    if len(answer.encode()) > 32000:
        raise ValueError("Oversized answer")
    nonce = secrets.token_bytes(12)
    return {"sealed": b64(nonce + cipher.encrypt(nonce, answer.encode(), prefix + b"answer"))}


if __name__ == "__main__":
    if sys.argv[1:] != ["pair"] or not sys.stdout.isatty():
        raise SystemExit("Run pair from the local Odin terminal")
    CONFIG.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        fd = os.open(CONFIG / "browser.key", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "wb") as handle:
            handle.write(secrets.token_bytes(32))
    print("Enter this pairing code once in your trusted browser:", b64(pairing_key()))
