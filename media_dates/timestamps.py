import os
import shutil
import subprocess


def set_mtime(path, dt):
    """
    Change filesystem modification time while preserving access time.
    """
    stat = path.stat()

    os.utime(
        path,
        (
            stat.st_atime,
            dt.timestamp(),
        ),
    )


def windows_path(path):
    """
    Convert a WSL path to a Windows path.
    """
    result = subprocess.run(
        ["wslpath", "-w", str(path.resolve())],
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout.strip()


def set_windows_creation_time(path, dt):
    """
    Change Windows CreationTime from WSL.

    This is WSL-only.
    """
    if not shutil.which("powershell.exe"):
        raise RuntimeError(
            "powershell.exe not found; --creation is only supported under WSL."
        )

    if not shutil.which("wslpath"):
        raise RuntimeError(
            "wslpath not found; --creation is only supported under WSL."
        )

    win_path = windows_path(path)

    env = os.environ.copy()
    env["TARGET_FILE"] = win_path
    env["TARGET_TIME"] = dt.isoformat()

    command = r"""
$p = $env:TARGET_FILE
$t = [DateTimeOffset]::Parse($env:TARGET_TIME)
[System.IO.File]::SetCreationTime($p, $t.LocalDateTime)
"""

    subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def format_dt(dt):
    if dt is None:
        return "MISSING"

    return dt.isoformat(
        sep=" ",
        timespec="seconds",
    )


def apply_timestamps(files, metadata, creation=False):
    """
    Apply target timestamps.

    Returns:
        changed, skipped, errors, changed_files
    """
    changed = 0
    skipped = 0
    errors = []
    changed_files = []

    for path in files:
        info = metadata[path]
        dt = info["datetime"]

        if dt is None:
            skipped += 1
            continue

        current_mtime_ns = path.stat().st_mtime_ns
        target_mtime_ns = round(dt.timestamp() * 1_000_000_000)

        if current_mtime_ns == target_mtime_ns and not creation:
            skipped += 1
            continue

        try:
            if current_mtime_ns != target_mtime_ns:
                set_mtime(path, dt)

            if creation:
                set_windows_creation_time(path, dt)

            changed += 1
            changed_files.append(path)

        except Exception as exc:
            errors.append((path, exc))

    return changed, skipped, errors, changed_files
