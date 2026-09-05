#!/usr/bin/env python3
"""Fetch golden-set sources from PokeMiners into the local cache.

Downloads only files that exist in the GitHub tree listing (no guessed paths):
  - numbered Pokemon - 256x256 base + shiny for each golden dex
  - 256 Addressable pm{dex}[.fFORM].icon.png (no costumes, no shiny)
  - Rocket/shadow_icon.png
  - TiMXL uicons-outline pokemon files for QA comparison

Requires .cache/tree_256.json and .cache/tree_addr.json (GitHub git/trees
listings for "Images/Pokemon - 256x256" and its "Addressable Assets").
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE = REPO_ROOT / ".cache"
POGO = CACHE / "pogo_assets" / "Images"
PX256_DIR = POGO / "Pokemon - 256x256"
ADDR_DIR = PX256_DIR / "Addressable Assets"
TIMXL_DIR = CACHE / "timxl" / "pokemon"

RAW_MINERS = "https://raw.githubusercontent.com/PokeMiners/pogo_assets/master/"
RAW_TIMXL = "https://raw.githubusercontent.com/TiMXL73/PogoAssets/main/uicons-outline/pokemon/"


def golden_names() -> list[str]:
    out = []
    for line in (REPO_ROOT / "tools" / "golden.txt").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def fetch(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
    except Exception as e:
        print(f"MISS {url} ({e})")
        return False
    dest.write_bytes(data)
    print(f"ok   {dest.relative_to(CACHE)} ({len(data)} bytes)")
    return True


def main() -> int:
    tree_256 = json.load(open(CACHE / "tree_256.json"))
    tree_addr = json.load(open(CACHE / "tree_addr.json"))
    names_256 = {t["path"] for t in tree_256["tree"] if t["type"] == "blob"}
    names_addr = {t["path"] for t in tree_addr["tree"] if t["type"] == "blob"}

    golden = golden_names()
    dexes = sorted({n.split("_", 1)[0].replace(".png", "") for n in golden}, key=int)
    print("golden dexes:", dexes)

    failures = []

    # Numbered 256: base + shiny when present in the listing.
    for dex in dexes:
        d3 = f"{int(dex):03d}"
        for name in (f"pokemon_icon_{d3}_00.png", f"pokemon_icon_{d3}_00_shiny.png"):
            if name in names_256:
                url = RAW_MINERS + urllib.parse.quote(f"Images/Pokemon - 256x256/{name}")
                if not fetch(url, PX256_DIR / name):
                    failures.append(name)

    # 256 Addressable: pm{dex} and pm{dex}.fFORM, no costume, no shiny.
    addr_re = {dex: re.compile(rf"^pm{dex}(\.f[^.]+)?\.icon\.png$") for dex in dexes}
    for name in sorted(names_addr):
        for dex, rx in addr_re.items():
            if rx.match(name):
                url = RAW_MINERS + urllib.parse.quote(
                    f"Images/Pokemon - 256x256/Addressable Assets/{name}"
                )
                if not fetch(url, ADDR_DIR / name):
                    failures.append(name)

    # Shadow smoke.
    if not fetch(RAW_MINERS + "Images/Rocket/shadow_icon.png", POGO / "Rocket" / "shadow_icon.png"):
        failures.append("shadow_icon.png")

    # TiMXL comparison icons (missing files are reported, not fatal).
    for name in golden:
        fetch(RAW_TIMXL + name, TIMXL_DIR / name)

    if failures:
        print("FAILED:", failures)
        return 1
    print("all PokeMiners sources fetched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
