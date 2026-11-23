"""Read-only inventory of *potential* Android integration points for Odin.

This probes the PATH, not Android permissions or live device functionality.
No subprocesses, network requests, app launches, key events, or writes.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import UTC, datetime

# Every item requires separate live verification and explicit permissions.
COMMANDS = (
    ("battery_read", "termux-battery-status", "read", "Battery status via Termux:API"),
    ("sensor_read", "termux-sensor", "sensitive_read", "Sensor metadata/data, explicit access"),
    ("audio_volume", "termux-volume", "reversible", "Read or set audio volume"),
    ("screen_brightness", "termux-brightness", "reversible", "Brightness with Android permission"),
    ("network_status", "termux-wifi-connectioninfo", "sensitive_read", "Wi-Fi details (private)"),
    ("media_controls", "termux-media-player", "reversible", "Media transport controls"),
    ("notifications", "termux-notification", "reversible", "Local notification triggers"),
    ("vibration", "termux-vibrate", "reversible", "Haptic feedback"),
    ("text_to_speech", "termux-tts-speak", "reversible", "Local speech output"),
    ("app_intents", "termux-open", "reversible", "Open approved Android intents/URLs"),
    ("adb_utility", "adb", "privileged_optional", "ADB binary; authorization not tested"),
    ("background_wakelock", "termux-wake-lock", "reversible", "Potential wake lock; not enabled"),
)

PLANNED_NATIVE_HOOKS = (
    ("native_companion", "Native Android companion app not yet built or installed"),
    ("accessibility", "Accessibility service not yet built or user-enabled"),
    ("physical_buttons", "Button mapping needs on-device key/input-event investigation"),
    ("shizuku", "Optional privileged integration requires Android 10 ADB setup"),
    ("secure_ipc", "App-to-Termux secure, authenticated local transport not yet built"),
)


def inventory(which=shutil.which, environ=None):
    env = os.environ if environ is None else environ
    android_context = bool(env.get("ANDROID_ROOT") or
                           env.get("PREFIX", "").startswith("/data/data/com.termux/"))
    result = []
    for ident, command, permission, description in COMMANDS:
        try:
            present = which(command) is not None
            detection = "DETECTED" if present else "NOT_DETECTED"
        except (OSError, ValueError, TypeError):
            present = False
            detection = "UNVERIFIED"
        result.append({
            "id": ident, "command": command, "permission_class": permission,
            "binary": detection, "operational": "UNVERIFIED",
            "description": description,
        })
    for ident, description in PLANNED_NATIVE_HOOKS:
        result.append({
            "id": ident, "command": None, "permission_class": "opt_in",
            "binary": "NOT_APPLICABLE", "operational": "UNVERIFIED",
            "description": description,
        })
    return {
        "schema_version": 1,
        "observed_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "scope": "read_only_path_inventory",
        "android_environment": "POSSIBLE" if android_context else "UNVERIFIED",
        "permission_state": "UNVERIFIED",
        "device_verification": "UNVERIFIED",
        "capabilities": result,
        "note": ("Executable presence alone does not prove permission, API add-on "
                 "installation, capability, ADB authorization, or Android control."),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print structured status")
    args = parser.parse_args(argv)
    data = inventory()
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print("Odin Android hook inventory — no permissions or live actions tested")
        for item in data["capabilities"]:
            print(f"{item['id']}: {item['binary']}; operational=UNVERIFIED")
        print("Not a device readiness or permission grant. See docs/ANDROID_INTEGRATION.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
