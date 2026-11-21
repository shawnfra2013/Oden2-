"""Stamp the hosted shell and its static asset URLs before publishing a UI change."""
import hashlib
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "mobile"
page = root / "index.html"
source = re.sub(r'<meta name="odin-release" content="[a-f0-9]+">\n?', "", page.read_text())
source = re.sub(r'\?v=[a-f0-9]{16}(?=")', '', source)
pattern = r'((?:src|href)="/([^"/?]+\.(?:css|js|webmanifest|svg)))"'
def stamp(match):
    digest = hashlib.sha256((root / match[2]).read_bytes()).hexdigest()[:16]
    return match[1] + "?v=" + digest + '"'
source = re.sub(pattern, stamp, source)
version = hashlib.sha256(source.encode()).hexdigest()[:16]
page.write_text(source.replace("<head>\n", f'<head>\n<meta name="odin-release" content="{version}">\n', 1))
