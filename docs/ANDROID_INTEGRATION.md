# Odin native Android integration — capabilities and permission gates

**Goal:** Make Odin on the AYN Odin M2 (Android 10) deeply integrated with legitimate device interfaces, without rooting, altering `/system`, opening unauthenticated network ports, or assuming access that has not been proven.

**Issue:** [#92](https://github.com/shawnfra2013/Oden2-/issues/92). **Status:** Discovery in progress. No Android settings, apps, privileges, or button mappings have been changed by this PR. GitHub CI tests only the source.

## First: read-only inventory

Run this command **on the handheld itself**, in its existing Termux workspace:

```bash
cd ~/odin-workspace || exit 1
python -B scripts/odin_android_capabilities.py --json
```

The report checks whether candidate command-line tools are visible in the process PATH. It **does not execute** those tools, start a daemon, read private data, grant permissions, request root, or contact a paid model. A detected executable means only that its binary is visible; its actual ability to operate remains **UNVERIFIED** until an approved, bounded live test is recorded.

Do not paste raw private Android configuration, ADB identifiers, key events, Wi-Fi details, screenshots, or pairing secrets into a public GitHub issue.

## Integration layers, ordered by least privilege

| Layer | Potential hooks | Prerequisite and limit |
| --- | --- | --- |
| **Termux:API add-on** | Battery, sensors, vibration, media, notifications, volume, speech, brightness | Requires a compatible add-on and matching Termux API package; individual Android permissions may be needed |
| **Android intents** | Open approved applications or URLs, share data using Android's normal mechanisms | Must validate exact intents/package names and require user authorization for side effects |
| **Native companion app** | App lifecycle, foreground notification, event collection, hardware button hooks when supported | Needs a built and installed Android APK with clearly declared/scoped permissions |
| **Accessibility service (optional)** | Explicitly approved navigation, eligible key events, screen actions | User must manually enable this sensitive Android capability; service can be disabled/revoked; no background monitoring by default |
| **ADB/Shizuku (optional)** | Additional system-level commands unavailable to a normal app | Android 10 generally requires user-authorized ADB setup; not equivalent to root or kernel access; service may need reactivation after reboot |
| **Root/kernel** | Direct kernel or protected system changes | **Excluded from the default plan**: risks device integrity, security, warranty and data |

## Non-negotiable safety contracts

- Capabilities are `PASS`, `FAIL`, or `UNVERIFIED` **per operation**, with dated evidence; file or CLI presence must never claim operational success.
- Separate `read_only`, `reversible`, `sensitive`, and `privileged` commands. Require explicit per-feature opt-in for the last two, and record user-revocable grants.
- Build a small modular Android bridge rather than giving the model arbitrary shell, `adb shell`, app-install, key injection, or administrative access.
- Only explicit allowlisted actions with validated parameters, timeouts, correlation IDs, bounded receipts, and privacy-safe audit records.
- The companion must be local/private, never exposed directly to the public internet. Tailscale and GitHub mailbox continue to be distinct approved transports.
- Any button remapping must preserve an obvious manual exit/revoke path and cannot assume all buttons are interceptable.
- No installation, access-service activation, rooting, `/system` modifications or device-settings changes based only on GitHub Actions.

## Definition of progress

1. **Source inventory:** deterministic discovery logic and unit tests pass in GitHub.
2. **Device capability matrix:** operator runs read-only discovery on Odin; log available, missing and unknown hooks.
3. **Termux:API live tests:** with explicit approval, test one harmless read (such as battery level), then one reversible action and confirm receipt/rollback.
4. **Companion prototype:** build native Android app with permission UI, secure local IPC, and one harmless bounded device action; review security before installation.
5. **Buttons, lifecycle and elevated hooks:** separate acceptance for each supported API, input device, Accessibility or ADB/Shizuku action.
6. **Release:** source SHA checks, actual Android proof and iPhone path proof. Never mark an issue done on code upload alone.

Sources: [Termux:API](https://github.com/termux/termux-api), [Android AccessibilityService](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService), [Android background limits](https://developer.android.com/about/versions/oreo/background), [Shizuku official setup](https://shizuku.rikka.app/guide/setup/).
