#!/usr/bin/env python3

import sys

from media_dates.cli import run_cli
from media_dates.gui import run_gui


def main():
    if "--gui" in sys.argv:
        sys.argv.remove("--gui")
        run_gui()
    else:
        run_cli()


if __name__ == "__main__":
    main()
