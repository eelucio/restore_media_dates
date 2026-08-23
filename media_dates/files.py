from .constants import EXTENSIONS
from .metadata import sequence_number


def collect_files(folder, recursive=False):
    """
    Collect supported media files.
    """
    paths = folder.rglob("*") if recursive else folder.iterdir()

    files = [
        path.resolve()
        for path in paths
        if path.is_file() and path.suffix.lower() in EXTENSIONS
    ]

    files.sort(
        key=lambda path: (
            str(path.parent),
            sequence_number(path)
            if sequence_number(path) is not None
            else float("inf"),
            path.name.lower(),
        )
    )

    return files
