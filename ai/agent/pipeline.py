"""Deterministic proposal identity and confined, non-overwriting file publication."""
import contextlib
import ctypes
import hashlib
import json
import os
import stat
import uuid
from pathlib import Path

MAX_SOURCE = 50000
SCHEMA = 1


def task_id(value):
    if not isinstance(value, str) or len(value) != 12:
        raise ValueError("Invalid task ID")
    if any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Invalid task ID")
    return value


def invocation_id(value):
    if not isinstance(value, str) or len(value) != 32:
        raise ValueError("Invalid invocation ID")
    if any(c not in "0123456789abcdef" for c in value):
        raise ValueError("Invalid invocation ID")
    return value


def target_parts(name):
    if not isinstance(name, str) or len(name) > 240:
        raise ValueError("Invalid target")
    path = Path(name)
    if (path.is_absolute() or path.as_posix() != name or ".." in path.parts
            or path.suffix != ".py" or len(path.parts) < 2
            or path.parts[0] not in {"ai", "tests"}):
        raise ValueError("Target must be a Python module in ai/ or tests/")
    return path.parts


def parts(value):
    result = tuple(value)
    if not result or any(not isinstance(p, str) or p in {"", ".", ".."}
                         or "/" in p or "\x00" in p for p in result):
        raise ValueError("Unsafe relative path")
    return result


@contextlib.contextmanager
def directory(root, relative=(), *, create=False):
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in relative:
            parts((component,))
            if create:
                try:
                    os.mkdir(component, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def read(root, relative, limit=MAX_SOURCE):
    relative = parts(relative)
    with directory(root, relative[:-1]) as parent:
        fd = os.open(relative[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=parent)
        with os.fdopen(fd, "rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise ValueError("Invalid file type or size")
            data = handle.read(limit + 1)
            after = os.fstat(handle.fileno())
        current = os.stat(relative[-1], dir_fd=parent, follow_symlinks=False)
    signatures = {(s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                  for s in (before, after, current)}
    if len(signatures) != 1 or len(data) > limit:
        raise ValueError("File changed during read")
    return data


def link_new(source, destination, *, src_dir_fd, dst_dir_fd):
    """Create a non-overwriting hard link, including on Android Python."""
    native = getattr(os, "link", None)
    if callable(native):
        native(source, destination, src_dir_fd=src_dir_fd,
               dst_dir_fd=dst_dir_fd, follow_symlinks=False)
        return
    try:
        linkat = ctypes.CDLL(None, use_errno=True).linkat
    except AttributeError as error:
        raise RuntimeError("Atomic no-overwrite publication requires libc linkat") from error
    linkat.argtypes = [ctypes.c_int, ctypes.c_char_p,
                       ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    linkat.restype = ctypes.c_int
    if linkat(src_dir_fd, os.fsencode(source), dst_dir_fd,
              os.fsencode(destination), 0) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), destination)


def publish(root, relative, data, *, replace=False):
    """Publish full bytes atomically; new files never replace existing evidence."""
    relative = parts(relative)
    if not isinstance(data, bytes):
        raise TypeError("Expected bytes")
    with directory(root, relative[:-1], create=True) as parent:
        temporary = ".odin-" + uuid.uuid4().hex + ".tmp"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            if replace:
                try:
                    mode = os.stat(relative[-1], dir_fd=parent,
                                   follow_symlinks=False).st_mode
                except FileNotFoundError:
                    mode = stat.S_IFREG
                if not stat.S_ISREG(mode):
                    raise ValueError("Refusing non-regular destination")
                os.replace(temporary, relative[-1], src_dir_fd=parent, dst_dir_fd=parent)
            else:
                link_new(temporary, relative[-1], src_dir_fd=parent,
                         dst_dir_fd=parent)
                os.unlink(temporary, dir_fd=parent)
            os.fsync(parent)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=parent)


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def move_new(root, source, destination):
    source, destination = parts(source), parts(destination)
    with directory(root, source[:-1]) as src, directory(root, destination[:-1], create=True) as dst:
        if not stat.S_ISREG(os.stat(source[-1], dir_fd=src, follow_symlinks=False).st_mode):
            raise ValueError("Queue source is not a regular file")
        link_new(source[-1], destination[-1], src_dir_fd=src, dst_dir_fd=dst)
        os.unlink(source[-1], dir_fd=src)
        os.fsync(src)
        os.fsync(dst)


def unlink(root, relative):
    relative = parts(relative)
    with directory(root, relative[:-1]) as parent:
        os.unlink(relative[-1], dir_fd=parent)
        os.fsync(parent)


def baseline(root, name):
    relative = target_parts(name)
    try:
        data = read(root, relative, 30000)
    except FileNotFoundError:
        return None, ""
    return hashlib.sha256(data).hexdigest(), data.decode("utf-8")


def proposal_parts(owner, invocation):
    owner = "interactive" if owner is None else task_id(owner)
    invocation_id(invocation)
    return ("state", "proposals", "invocations", owner, invocation)


def reserve(root, owner, invocation):
    relative = proposal_parts(owner, invocation)
    with directory(root, relative[:-1], create=True) as parent:
        os.mkdir(relative[-1], 0o700, dir_fd=parent)
        os.fsync(parent)
    return relative


def receipt(root, name, task, owner, invocation):
    relative = proposal_parts(owner, invocation)
    data = read(root, (*relative, "candidate.py"))
    meta = json.loads(read(root, (*relative, "metadata.json"), 20000))
    expected = {"schema": SCHEMA, "target": name, "task": task, "task_id": owner,
                "invocation_id": invocation, "syntax": "passed", "ruff": "passed",
                "applied": False, "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data), "baseline_sha256": baseline(root, name)[0]}
    if not isinstance(meta, dict) or any(type(meta.get(k)) is not type(v) or meta.get(k) != v
                                         for k, v in expected.items()):
        raise ValueError("Proposal identity, content, or baseline mismatch")
    if meta.get("applied") is not False or not data:
        raise ValueError("Invalid proposal state")
    return data, {**expected, "artifact": str(Path(root).joinpath(*relative, "candidate.py")),
                  "metadata": str(Path(root).joinpath(*relative, "metadata.json"))}
