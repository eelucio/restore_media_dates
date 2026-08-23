import sys
from pathlib import Path


DESKTOP_ENTRY_NAME = "restore-media-dates.desktop"


def quote_desktop_argument(value):
    """Quote one argument according to the Desktop Entry Exec syntax."""
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def install_desktop_entry(destination=None):
    """Create or update the current user's Ubuntu application launcher."""
    project_root = Path(__file__).resolve().parents[1]
    launcher = destination or (
        Path.home() / ".local" / "share" / "applications" / DESKTOP_ENTRY_NAME
    )
    launcher = Path(launcher)

    python = quote_desktop_argument(sys.executable)
    script = quote_desktop_argument(project_root / "restore_media_dates.py")

    content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Restore Media Dates
Comment=Restore media filesystem dates from embedded metadata
Exec={python} {script} --gui
Icon=camera-photo
Terminal=false
Categories=Utility;Graphics;
StartupNotify=true
"""

    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(content, encoding="utf-8")
    return launcher
