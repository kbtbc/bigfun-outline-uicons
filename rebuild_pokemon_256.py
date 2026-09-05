#!/usr/bin/env python3
"""Wrapper — canonical rebuild lives in tools/rebuild_pokemon_256.py."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parent / "tools" / "rebuild_pokemon_256.py"
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name="__main__")
