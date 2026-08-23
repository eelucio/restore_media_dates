import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .metadata import write_missing_datetime_original
from .scan import prepare_scan
from .timestamps import apply_timestamps, format_dt


def run_gui():
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
        from tkinter.scrolledtext import ScrolledText
    except ImportError:
        print(
            "Tkinter is not installed.\n"
            "On Ubuntu install it with:\n\n"
            "  sudo apt install python3-tk",
            file=sys.stderr,
        )
        sys.exit(1)

    root = tk.Tk()
    root.title("Restore Photo Dates")
    root.geometry("1000x650")

    folder_var = tk.StringVar(value=str(Path.home() / "Pictures"))
    recursive_var = tk.BooleanVar(value=True)
    infer_var = tk.BooleanVar(value=True)
    creation_var = tk.BooleanVar(value=False)
    write_original_var = tk.BooleanVar(value=False)

    top = tk.Frame(root)
    top.pack(
        fill="x",
        padx=10,
        pady=10,
    )

    tk.Label(
        top,
        text="Folder:",
    ).pack(side="left")

    folder_entry = tk.Entry(
        top,
        textvariable=folder_var,
    )
    folder_entry.pack(
        side="left",
        fill="x",
        expand=True,
        padx=5,
    )

    def browse():
        folder = filedialog.askdirectory(
            initialdir=folder_var.get()
        )

        if folder:
            folder_var.set(folder)

    tk.Button(
        top,
        text="Browse",
        command=browse,
    ).pack(side="right")

    options = tk.Frame(root)
    options.pack(
        fill="x",
        padx=10,
    )

    tk.Checkbutton(
        options,
        text="Include subfolders",
        variable=recursive_var,
    ).pack(side="left")

    tk.Checkbutton(
        options,
        text="Infer missing dates",
        variable=infer_var,
    ).pack(
        side="left",
        padx=20,
    )

    creation_checkbox = tk.Checkbutton(
        options,
        text="Also set Windows CreationTime (WSL only)",
        variable=creation_var,
    )
    creation_checkbox.pack(side="left")

    tk.Checkbutton(
        options,
        text="Write missing EXIF DateTimeOriginal",
        variable=write_original_var,
    ).pack(
        side="left",
        padx=20,
    )

    if not shutil.which("powershell.exe"):
        creation_checkbox.configure(state="disabled")
        creation_var.set(False)

    output = ScrolledText(
        root,
        wrap="none",
        font=("monospace", 10),
    )
    output.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=10,
    )

    current_data = {
        "folder": None,
        "files": [],
        "metadata": {},
    }

    status_var = tk.StringVar(value="Ready.")

    status = tk.Label(
        root,
        textvariable=status_var,
        anchor="w",
    )
    status.pack(
        fill="x",
        padx=10,
        pady=(0, 5),
    )

    def scan():
        try:
            folder, files, metadata = prepare_scan(
                folder_var.get(),
                recursive=recursive_var.get(),
                infer=infer_var.get(),
            )
        except subprocess.CalledProcessError as exc:
            messagebox.showerror(
                "ExifTool error",
                exc.stderr or str(exc),
            )
            return False
        except Exception as exc:
            messagebox.showerror(
                "Error",
                str(exc),
            )
            return False

        if not files:
            messagebox.showinfo(
                "No files",
                "No supported media files were found.",
            )
            return False

        current_data["folder"] = folder
        current_data["files"] = files
        current_data["metadata"] = metadata

        output.delete(
            "1.0",
            tk.END,
        )

        output.insert(
            tk.END,
            (
                f"{'FILE':50} "
                f"{'CURRENT MTIME':27} "
                f"{'NEW MTIME':27} "
                f"SOURCE\n"
            ),
        )
        output.insert(
            tk.END,
            "-" * 120 + "\n",
        )

        missing = 0
        inferred = 0

        for path in files:
            info = metadata[path]

            try:
                display_path = path.relative_to(folder)
            except ValueError:
                display_path = path

            source = info["source"] or "NO DATE"

            if info["datetime"] is None:
                missing += 1

            if source.startswith("inferred"):
                inferred += 1

            current_mtime = datetime.fromtimestamp(
                path.stat().st_mtime
            ).astimezone()

            output.insert(
                tk.END,
                (
                    f"{str(display_path):50} "
                    f"{format_dt(current_mtime):27} "
                    f"{format_dt(info['datetime']):27} "
                    f"{source}\n"
                ),
            )

        status_var.set(
            (
                f"{len(files)} files | "
                f"{inferred} inferred | "
                f"{missing} without date"
            )
        )

        return True

    def preview():
        scan()

    def apply():
        if not scan():
            return

        files = current_data["files"]
        metadata = current_data["metadata"]

        count = sum(
            metadata[path]["datetime"] is not None
            for path in files
        )

        inferred_count = sum(
            (metadata[path]["source"] or "").startswith("inferred")
            for path in files
        )

        message = f"Change modification time for {count} files?"

        if inferred_count:
            message += f"\n\n{inferred_count} of these use inferred timestamps."

        if creation_var.get():
            message += "\n\nWindows CreationTime will also be changed."

        if write_original_var.get():
            message += (
                "\n\nMissing EXIF DateTimeOriginal values will be written "
                "to HEIC/JPG/JPEG files."
            )

        if not messagebox.askyesno(
            "Confirm changes",
            message,
        ):
            return

        metadata_changed = 0
        metadata_skipped = 0
        metadata_errors = []

        if write_original_var.get():
            (
                metadata_changed,
                metadata_skipped,
                metadata_errors,
                _metadata_changed_files,
            ) = (
                write_missing_datetime_original(files, metadata)
            )

        changed, skipped, errors, _changed_files = apply_timestamps(
            files,
            metadata,
            creation=creation_var.get(),
        )

        errors = metadata_errors + errors

        result = f"Updated: {changed}\nSkipped: {skipped}"
        if write_original_var.get():
            result += (
                f"\nDateTimeOriginal created: {metadata_changed}"
                f"\nDateTimeOriginal skipped: {metadata_skipped}"
            )

        if errors:
            error_text = "\n".join(
                f"{path.name}: {exc}"
                for path, exc in errors[:10]
            )

            if len(errors) > 10:
                error_text += f"\n... and {len(errors) - 10} more"

            messagebox.showwarning(
                "Finished with errors",
                (
                    f"{result}\n"
                    f"Errors: {len(errors)}\n\n"
                    f"{error_text}"
                ),
            )
        else:
            messagebox.showinfo(
                "Finished",
                result,
            )

    buttons = tk.Frame(root)
    buttons.pack(pady=(0, 10))

    tk.Button(
        buttons,
        text="Preview",
        width=15,
        command=preview,
    ).pack(
        side="left",
        padx=5,
    )

    tk.Button(
        buttons,
        text="Apply",
        width=15,
        command=apply,
    ).pack(
        side="left",
        padx=5,
    )

    root.mainloop()
