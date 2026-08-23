from pathlib import Path

from .files import collect_files
from .inference import infer_per_folder
from .metadata import read_metadata


def prepare_scan(folder, recursive=False, infer=True):
    """
    Scan a folder and return files + metadata.
    """
    folder = Path(folder).resolve()

    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder}")

    files = collect_files(
        folder,
        recursive=recursive,
    )

    if not files:
        return folder, [], {}

    metadata = read_metadata(files)

    if infer:
        infer_per_folder(files, metadata)

    return folder, files, metadata
