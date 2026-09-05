#!/usr/bin/env python3
"""Shared path defaults for bigfun-outline-uicons tools.

Override with env:
  POGO_ASSETS / BIGFUN_POGO_ASSETS
  MASTER_JSON
  BIGFUN_OUT          pokemon output dir
  BIGFUN_ENHANCE_DIR  directory containing enhance_all.py
  WWM_SRC             optional WatWowMap checkout (legacy fallback)
"""
from __future__ import annotations

import os
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
POGO_ASSETS = Path(
    os.environ.get("POGO_ASSETS")
    or os.environ.get("BIGFUN_POGO_ASSETS")
    or "/workspace/pogo_assets"
)
MASTER_JSON = Path(os.environ.get("MASTER_JSON", "/workspace/master-latest.json"))
WWM_SRC = Path(os.environ.get("WWM_SRC", "/workspace/wwm-uicons/src"))
