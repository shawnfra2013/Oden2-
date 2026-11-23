"""Enroll one Tailscale IPv4 peer for the Odin web app."""
import argparse
import ipaddress
import os
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

PORT = 8766
TAILNET = ipaddress.IPv4Network("100.64.0.0/10")


def addresses(values):
    if len(values) != 2:
        raise ValueError("Enter Odin and iPhone Tailscale IPv4 addresses")
    odin, phone = map(ipaddress.IPv4Address, values)
    if odin not in TAILNET or phone not in TAILNET or odin == phone:
        raise ValueError("Enter two distinct Tailscale IPv4 addresses")
    return str(odin), str(phone)


def config_path():
    return Path.home() / ".config" / "odin-web" / "phone-peer"


def configuration():
    try:
        return addresses(config_path().read_text().split())
    except FileNotFoundError:
        return None


def serve_phone(local, handler, config, stop):
    odin, phone = config
    while not stop.is_set():
        try:
            listener = ThreadingHTTPServer((odin, PORT), handler)
        except OSError:
            print("Waiting for Odin's Tailscale address on port 8766", flush=True)
            stop.wait(15)
            continue
        with listener:
            listener.request_host = f"{odin}:{PORT}"
            listener.allowed_peer = phone
            listener.session_token = local.session_token
            listener.conversations = local.conversations
            listener.chat_lock = local.chat_lock
            listener.timeout = 1
            print(f"Odin phone access: http://{listener.request_host}/", flush=True)
            while not stop.is_set():
                listener.handle_request()


def start(local, handler):
    stop = threading.Event()
    try:
        config = configuration()
    except (OSError, ValueError):
        print("Invalid Odin phone configuration. Local web app is available.", flush=True)
        return stop
    if config:
        threading.Thread(target=serve_phone, args=(local, handler, config, stop),
                         daemon=True).start()
    return stop


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("odin", help="Odin Tailscale IPv4")
    parser.add_argument("iphone", help="iPhone Tailscale IPv4")
    args = parser.parse_args()
    try:
        odin, phone = addresses([args.odin, args.iphone])
    except ValueError as error:
        parser.error(str(error))
    path = config_path()
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
        temp = Path(output.name)
        try:
            output.write(f"{odin}\n{phone}\n")
            output.flush()
            os.fsync(output.fileno())
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
    print(f"Phone configured. After restarting the web app, open http://{odin}:{PORT}/")


if __name__ == "__main__":
    main()
