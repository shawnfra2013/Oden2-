"""Wait for an authenticated work hint, preserving the normal reconciliation timer."""
import json
import time
from urllib.request import Request, urlopen

try:
    from .odin_relay_client import read_token
except ImportError:
    from odin_relay_client import read_token


def wait_for_work(lane, interval):
    deadline = time.monotonic() + interval
    try:
        req = Request("https://odin-control.vercel.app/api/wake?lane=" + lane,
                      headers={"Authorization": "Bearer " + read_token()})
        while deadline - time.monotonic() >= 21:
            started = time.monotonic()
            with urlopen(req, timeout=min(25, deadline - started)) as response:
                result = json.loads(response.read(256))
            if result.get("wake") is True:
                return
            if result.get("wake") is not False or time.monotonic() - started < 1:
                break
    except (ValueError, OSError, RuntimeError, AttributeError):
        pass
    time.sleep(max(0, deadline - time.monotonic()))


if __name__ == "__main__":
    wait_for_work("sync", 300)
