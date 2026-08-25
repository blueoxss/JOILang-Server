#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

VERSION_ROOT = Path(__file__).resolve().parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from scripts.export_joi_code_side_by_side_report import main


if __name__ == "__main__":
    raise SystemExit(main())
