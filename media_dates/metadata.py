import json
import re
import subprocess
from datetime import datetime
from pathlib import Path


def sequence_number(path):
    """
    Extract the final numeric part of the filename.

    IMG_4573.heic -> 4573
    IMG_4576.mov  -> 4576
    """
    match = re.search(r"(\d+)$", path.stem)
    return int(match.group(1)) if match else None


def parse_exif_datetime(value, offset=None):
    """
    Parse ExifTool timestamps such as:

      2024:05:27 20:57:29
      2024:05:27 20:57:29.893
      2024:05:27 21:12:12+02:00
    """
    if not value:
        return None

    value = str(value).strip()

    if offset and not re.search(r"[+-]\d\d:\d\d$", value):
        value += offset

    match = re.match(
        r"(\d{4}):(\d{2}):(\d{2})[ T](.*)",
        value,
    )

    if not match:
        return None

    iso = (
        f"{match.group(1)}-"
        f"{match.group(2)}-"
        f"{match.group(3)}T"
        f"{match.group(4)}"
    )

    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return None


def read_metadata(files):
    """
    Read capture timestamps from supported media using ExifTool.

    Photos:
        DateTimeOriginal

    MOV:
        Keys:CreationDate
    """
    cmd = [
        "exiftool",
        "-G1",
        "-j",
        "-DateTimeOriginal",
        "-OffsetTimeOriginal",
        "-Keys:CreationDate",
    ] + [str(file_path) for file_path in files]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)
    metadata = {}

    for item in data:
        source = Path(item["SourceFile"]).resolve()
        ext = source.suffix.lower()

        dt = None
        tag = None
        has_datetime_original = False

        if ext in {".heic", ".jpg", ".jpeg"}:
            value = (
                item.get("ExifIFD:DateTimeOriginal")
                or item.get("IFD0:DateTimeOriginal")
                or item.get("DateTimeOriginal")
            )
            has_datetime_original = bool(value)

            offset = (
                item.get("ExifIFD:OffsetTimeOriginal")
                or item.get("OffsetTimeOriginal")
            )

            dt = parse_exif_datetime(value, offset)

            if dt:
                tag = "DateTimeOriginal"

        elif ext == ".mov":
            value = item.get("Keys:CreationDate") or item.get("CreationDate")
            dt = parse_exif_datetime(value)

            if dt:
                tag = "Keys:CreationDate"

        metadata[source] = {
            "datetime": dt,
            "source": tag,
            "has_datetime_original": has_datetime_original,
        }

    return metadata


def format_exif_datetime(dt):
    """Format a datetime for ExifTool's EXIF date assignment."""
    return dt.strftime("%Y:%m:%d %H:%M:%S")


def format_exif_offset(dt):
    """Return an EXIF UTC offset, when the datetime is timezone-aware."""
    offset = dt.utcoffset()

    if offset is None:
        return None

    minutes = int(offset.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    hours, minutes = divmod(minutes, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def write_missing_datetime_original(files, metadata):
    """Create DateTimeOriginal for dated photos that do not already have it."""
    changed = 0
    skipped = 0
    errors = []
    changed_files = []

    for path in files:
        info = metadata[path]

        if (
            path.suffix.lower() not in {".heic", ".jpg", ".jpeg"}
            or info["has_datetime_original"]
            or info["datetime"] is None
        ):
            skipped += 1
            continue

        command = [
            "exiftool",
            "-overwrite_original",
            f"-DateTimeOriginal={format_exif_datetime(info['datetime'])}",
        ]

        offset = format_exif_offset(info["datetime"])
        if offset:
            command.append(f"-OffsetTimeOriginal={offset}")

        command.append(str(path))

        try:
            subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
            changed += 1
            changed_files.append(path)
        except Exception as exc:
            errors.append((path, exc))

    return changed, skipped, errors, changed_files
