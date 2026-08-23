from .metadata import sequence_number


def infer_missing(files, metadata):
    """
    Infer missing timestamps from numeric filename order.

    Strategy:
      1. If known timestamps exist on both sides:
         linearly interpolate.

      2. If only one known side exists:
         copy the nearest known timestamp.

    This function should be called separately for each directory.
    """
    numbered = []

    for path in files:
        number = sequence_number(path)

        if number is not None:
            numbered.append((number, path))

    numbered.sort()

    known = [
        (number, path, metadata[path]["datetime"])
        for number, path in numbered
        if metadata[path]["datetime"] is not None
    ]

    for number, path in numbered:
        if metadata[path]["datetime"] is not None:
            continue

        lower = [item for item in known if item[0] < number]
        upper = [item for item in known if item[0] > number]

        lower = lower[-1] if lower else None
        upper = upper[0] if upper else None

        if lower and upper:
            n1, _, t1 = lower
            n2, _, t2 = upper

            fraction = (number - n1) / (n2 - n1)
            inferred = t1 + (t2 - t1) * fraction

            metadata[path]["datetime"] = inferred
            metadata[path]["source"] = f"inferred between IMG_{n1} and IMG_{n2}"

        elif lower:
            n1, _, t1 = lower
            metadata[path]["datetime"] = t1
            metadata[path]["source"] = f"inferred from nearest IMG_{n1}"

        elif upper:
            n2, _, t2 = upper
            metadata[path]["datetime"] = t2
            metadata[path]["source"] = f"inferred from nearest IMG_{n2}"


def infer_per_folder(files, metadata):
    """
    Apply inference independently inside each directory.
    """
    files_by_folder = {}

    for path in files:
        files_by_folder.setdefault(path.parent, []).append(path)

    for folder_files in files_by_folder.values():
        infer_missing(folder_files, metadata)
