#!/usr/bin/env python3
"""Portable launcher. Run `python3 lab.py --help`."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "plugin" / "runtime"))
from workshop_lab.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
