# Restore Media Dates

Current version: `1.0.0`

`restore_media_dates.py` restores the **filesystem timestamps** of photos and
videos from the dates already embedded in those files. It is useful after a
copy, download, archive extraction, or migration has given media files the
wrong displayed "modified" date.

Supported files: HEIC, JPG, JPEG, and MOV.

## What it reads

The program uses [ExifTool](https://exiftool.org/) to read existing metadata:

- HEIC/JPG/JPEG: `DateTimeOriginal` (and `OffsetTimeOriginal`, if present)
- MOV: `Keys:CreationDate`

ExifTool is used only for reading by default. The optional
`--write-missing-original` mode writes an EXIF date as described below.

## What it changes

By default, a run is a preview only. Nothing is modified until `--apply` is
provided or Apply is clicked in the GUI.

With `--apply`, the program changes the file's filesystem **modification time**
(`mtime`) to the embedded capture/creation date. It does not rewrite the media
file's EXIF, XMP, QuickTime, or other embedded metadata.

Files whose `mtime` already matches the selected date are left untouched and
reported as unchanged.

`--apply --write-missing-original` additionally creates EXIF
`DateTimeOriginal` for HEIC/JPG/JPEG files that do not already have that tag.
It never overwrites an existing `DateTimeOriginal`. The value comes from the
same date shown in the preview, so it may be an inferred value unless
`--no-infer` is used. When available, the matching `OffsetTimeOriginal` is
also written. MOV files are not changed by this option.

With `--apply --creation` under WSL, it also changes the Windows filesystem
**CreationTime** using PowerShell. This is optional and is not available on a
normal Linux installation.

## Filesystem dates in `stat`

The names can be misleading, especially on Linux:

| Field | Meaning | This tool's behavior |
| --- | --- | --- |
| `mtime` | When file contents were last modified. Often shown as “Date modified.” | Set to the embedded media date with `--apply`. |
| `atime` | When the file was last accessed/read. Filesystems may reduce or disable updates to it. | Preserved when `mtime` is changed. |
| `ctime` | On Linux/Unix, when file metadata last changed, such as permissions, name, or `mtime`. It is **not** creation time. | Cannot be set manually; it will normally update automatically when `mtime` is changed. |
| Birth time / CreationTime | When the filesystem record was created. Its availability and name vary by filesystem. | Unchanged by default. Set only by the optional WSL `--creation` mode. |

So after a normal `--apply`, `stat` should show a restored `mtime`, the same
`atime`, and a new/current `ctime`. That `ctime` change is expected and does
not mean the photo's embedded capture date was edited.

## Usage

Install ExifTool, then preview a folder:

```bash
python3 restore_media_dates.py /path/to/media
```

Apply the displayed modification dates:

```bash
python3 restore_media_dates.py --apply /path/to/media
```

Also create missing EXIF `DateTimeOriginal` values for photos:

```bash
python3 restore_media_dates.py --apply -w /path/to/media
```

Include subdirectories:

```bash
python3 restore_media_dates.py --apply --recursive /path/to/media
```

Under WSL, also set Windows CreationTime:

```bash
python3 restore_media_dates.py --apply --creation /path/to/media
```

Launch the graphical interface:

```bash
python3 restore_media_dates.py --gui
```

Show the installed version:

```bash
python3 restore_media_dates.py --version
```

## Installing on Ubuntu

For a personal installation, keep the whole project directory in a location
such as `~/apps/restore_media_dates` or `~/src/restore_media_dates`. This keeps
the script and its `media_dates` package together while separating tools from
your documents and downloads. Run it from that directory with `python3
restore_media_dates.py`.

Use `~/bin` only if you want to add a small command wrapper to your `PATH`; it
is not the right location for the entire project. For a system-wide or
shared-machine installation, `/opt/restore_media_dates` is the conventional
location. Update the launcher command below if you place the project there.

## Ubuntu launcher

On native Ubuntu, create an application-launcher entry for the GUI with:

```bash
python3 restore_media_dates.py --install-desktop-entry
```

It creates or updates
`~/.local/share/applications/restore-media-dates.desktop`. Search the Ubuntu
application menu for “Restore Media Dates”, then pin it to the dock if useful.

To create the entry manually instead, use this content (replace the script path
if the project is stored elsewhere):

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Restore Media Dates
Comment=Restore media filesystem dates from embedded metadata
Exec=/usr/bin/python3 /home/etor/work/tools/restore_media_dates/restore_media_dates.py --gui
Icon=camera-photo
Terminal=false
Categories=Utility;Graphics;
StartupNotify=true
```

This creates a Linux desktop launcher. When running under WSL, it does not add
an item to the Windows Start menu.

## Missing embedded dates

By default, files without a readable date can receive an inferred timestamp
based on neighboring filename sequence numbers in the same directory (for
example, `IMG_1001` and `IMG_1003`). Review the preview carefully: inferred
rows are labelled as such. Use `--no-infer` to skip those files instead.
