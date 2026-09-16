#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""백엔드 pip/venv 의존성 설정"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
PYTHON = VENV / "bin" / "python"
PIP = VENV / "bin" / "pip"
REQUIREMENTS = ROOT / "backend" / "requirements.txt"


def main() -> None:
    if not VENV.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)

    subprocess.run([str(PIP), "install", "--upgrade", "pip", "setuptools"], check=True)

    pkg_text = REQUIREMENTS.read_text(encoding="utf-8")
    for line in pkg_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        subprocess.run([str(PIP), "install", line], check=True)

    subprocess.run([str(PYTHON), "-c", "import fastapi, uvicorn, pydantic; print('OK')"], check=True)
    print("SETUP_DONE")


if __name__ == "__main__":
    main()
