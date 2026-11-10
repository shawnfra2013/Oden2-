import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


class CheckResult(TypedDict):
    name: str
    ok: bool
    details: str
    version: str | None


@dataclass(frozen=True, slots=True)
class HealthCheckConfig:
    timeout: float = 5.0
    git_path: Path = Path("git")
    ruff_path: Path = Path("ruff")
    adb_path: Path = Path("adb")
    worker_check_path: Path = Path("scripts/worker_check.sh")


def _run_command(
    cmd: list[str],
    timeout: float,
) -> subprocess.CompletedProcess[bytes]:
    """Execute a command with a timeout, raising on failure."""
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _format_result(
    name: str,
    proc: subprocess.CompletedProcess[bytes],
    version: str | None = None,
) -> CheckResult:
    """Create a uniform result dictionary from a subprocess execution."""
    ok = proc.returncode == 0
    details = proc.stdout.decode().strip() or proc.stderr.decode().strip()
    return CheckResult(name=name, ok=ok, details=details, version=version)


def _extract_version(output: str) -> str:
    """Return the first token that looks like a version number."""
    for token in output.split():
        if any(ch.isdigit() for ch in token):
            return token.strip()
    return ""


def check_git(config: HealthCheckConfig) -> CheckResult:
    """Verify that git is installed and reachable."""
    try:
        proc = _run_command([str(config.git_path), "--version"], config.timeout)
    except (subprocess.SubprocessError, OSError) as exc:
        return CheckResult(
            name="git",
            ok=False,
            details=str(exc),
            version=None,
        )
    version = _extract_version(proc.stdout.decode())
    return _format_result("git", proc, version or None)


def check_ruff(config: HealthCheckConfig) -> CheckResult:
    """Verify that ruff is installed and reachable."""
    try:
        proc = _run_command([str(config.ruff_path), "--version"], config.timeout)
    except (subprocess.SubprocessError, OSError) as exc:
        return CheckResult(
            name="ruff",
            ok=False,
            details=str(exc),
            version=None,
        )
    version = _extract_version(proc.stdout.decode())
    return _format_result("ruff", proc, version or None)


def check_adb(config: HealthCheckConfig) -> CheckResult:
    """Verify that adb is installed and reachable."""
    try:
        proc = _run_command([str(config.adb_path), "version"], config.timeout)
    except (subprocess.SubprocessError, OSError) as exc:
        return CheckResult(
            name="adb",
            ok=False,
            details=str(exc),
            version=None,
        )
    version = _extract_version(proc.stdout.decode())
    return _format_result("adb", proc, version or None)


def check_worker(config: HealthCheckConfig) -> CheckResult:
    """Check the Termux background worker service."""
    try:
        proc = _run_command(
            ["sv", "status", "odin-task-worker"],
            config.timeout,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return CheckResult(
            name="worker",
            ok=False,
            details=str(exc),
            version=None,
        )
    result = _format_result("worker", proc)
    result["ok"] = proc.returncode == 0 and proc.stdout.decode(errors="replace").lstrip().startswith("run:")
    return result


def run_all_checks(config: HealthCheckConfig | None = None) -> list[CheckResult]:
    """Execute all health checks and return a list of results."""
    cfg = config or HealthCheckConfig()
    return [
        check_git(cfg),
        check_ruff(cfg),
        check_adb(cfg),
        check_worker(cfg),
    ]


if __name__ == "__main__":
    results = run_all_checks()
    for res in results:
        status = "OK" if res["ok"] else "FAIL"
        version = f' (v{res["version"]})' if res["version"] else ""
        print(f'{res["name"]}: {status}{version} – {res["details"]}')
