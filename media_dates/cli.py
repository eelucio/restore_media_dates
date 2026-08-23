import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .desktop import install_desktop_entry
from .metadata import write_missing_datetime_original
from .scan import prepare_scan
from .timestamps import apply_timestamps, format_dt


def print_preview(folder, files, metadata):
    """
    Print scan results to stdout.
    """
    print()
    print(
        f"{'FILE':55} "
        f"{'CURRENT MTIME':28} "
        f"{'NEW MTIME':28} "
        f"SOURCE"
    )
    print("-" * 150)

    for path in files:
        info = metadata[path]

        try:
            display_path = path.relative_to(folder)
        except ValueError:
            display_path = path

        current_mtime = datetime.fromtimestamp(
            path.stat().st_mtime
        ).astimezone()

        print(
            f"{str(display_path):55} "
            f"{format_dt(current_mtime):28} "
            f"{format_dt(info['datetime']):28} "
            f"{info['source'] or 'NO DATE'}"
        )


def print_changed_files(label, folder, files):
    """Print paths changed by one operation."""
    if not files:
        return

    print(f"{label}:")
    for path in files:
        try:
            display_path = path.relative_to(folder)
        except ValueError:
            display_path = path
        print(f"  {display_path}")


def run_cli():
    parser = argparse.ArgumentParser(
        description=(
            "Restore photo/video filesystem timestamps "
            "from embedded metadata."
        )
    )

    parser.add_argument(
        "folder",
        nargs="?",
        default=".",
        help="Folder to process (default: current folder)",
    )

    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Process subdirectories recursively.",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Actually modify timestamps. "
            "Without this option, only preview."
        ),
    )

    parser.add_argument(
        "--creation",
        action="store_true",
        help=(
            "Also set Windows CreationTime. "
            "WSL only."
        ),
    )

    parser.add_argument(
        "--no-infer",
        action="store_true",
        help="Do not infer dates for files without metadata.",
    )

    parser.add_argument(
        "-w",
        "--write-missing-original",
        action="store_true",
        help=(
            "Create EXIF DateTimeOriginal for dated HEIC/JPG/JPEG files "
            "that do not already have it. Requires --apply."
        ),
    )

    parser.add_argument(
        "--install-desktop-entry",
        action="store_true",
        help="Create or update an Ubuntu application launcher for the GUI.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    if args.install_desktop_entry:
        launcher = install_desktop_entry()
        print(f"Ubuntu launcher installed: {launcher}")
        return

    if args.creation and not shutil.which("powershell.exe"):
        parser.error("--creation is only supported under WSL.")

    if args.write_missing_original and not args.apply:
        parser.error("--write-missing-original requires --apply.")

    try:
        folder, files, metadata = prepare_scan(
            args.folder,
            recursive=args.recursive,
            infer=not args.no_infer,
        )
    except subprocess.CalledProcessError as exc:
        print(
            f"ExifTool failed:\n{exc.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not files:
        print("No HEIC/JPG/JPEG/MOV files found.")
        return

    print_preview(
        folder,
        files,
        metadata,
    )

    if not args.apply:
        print()
        print("DRY RUN: nothing was modified.")

        print()
        print("Apply modification timestamps with:")

        cmd = [Path(sys.argv[0]).name]

        if args.recursive:
            cmd.append("-r")

        cmd.extend(
            [
                "--apply",
                str(folder),
            ]
        )

        print("  " + " ".join(cmd))

        if not args.creation:
            print()
            print("Under WSL, to also restore Windows CreationTime:")

            cmd_creation = [Path(sys.argv[0]).name]

            if args.recursive:
                cmd_creation.append("-r")

            cmd_creation.extend(
                [
                    "--apply",
                    "--creation",
                    str(folder),
                ]
            )

            print("  " + " ".join(cmd_creation))

        return

    print()
    print("Applying timestamps...")

    metadata_changed = 0
    metadata_skipped = 0
    metadata_errors = []

    if args.write_missing_original:
        print("Writing missing DateTimeOriginal values...")
        (
            metadata_changed,
            metadata_skipped,
            metadata_errors,
            metadata_changed_files,
        ) = (
            write_missing_datetime_original(files, metadata)
        )
    else:
        metadata_changed_files = []

    changed, skipped, errors, changed_files = apply_timestamps(
        files,
        metadata,
        creation=args.creation,
    )

    print()
    print(f"Updated: {changed}")
    print(f"Unchanged or missing date: {skipped}")

    if args.write_missing_original:
        print(f"DateTimeOriginal created: {metadata_changed}")
        print(f"DateTimeOriginal skipped: {metadata_skipped}")
        print_changed_files(
            "DateTimeOriginal written for",
            folder,
            metadata_changed_files,
        )

    print_changed_files("Timestamp updated for", folder, changed_files)

    all_errors = metadata_errors + errors

    if all_errors:
        print(f"Errors:  {len(all_errors)}")

        for path, exc in all_errors:
            print(f"ERROR {path}: {exc}")
