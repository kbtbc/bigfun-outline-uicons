#!/usr/bin/env python3
"""Public-contract checks that do not need PokeMiners sources."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UICONS_ROOT_KEYS = {
    "background",
    "device",
    "gym",
    "invasion",
    "misc",
    "nest",
    "pokemon",
    "pokestop",
    "raid",
    "reward",
    "spawnpoint",
    "station",
    "tappable",
    "team",
    "type",
    "weather",
}


def main() -> int:
    errors: list[str] = []
    index_path = ROOT / "index.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if ".git" in data:
        errors.append("index.json includes .git")
    extra = sorted(set(data) - UICONS_ROOT_KEYS)
    missing = sorted(UICONS_ROOT_KEYS - set(data))
    if extra:
        errors.append(f"index.json extra keys: {extra}")
    if missing:
        errors.append(f"index.json missing keys: {missing}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "93" in readme and "256" not in readme:
        errors.append("README still describes 93-only Pokémon sizing")
    if "wwm source art" in readme.lower() or "comes from the wwm source" in readme.lower():
        errors.append("README still says Shadow aura comes from wwm")
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    if pkg.get("name") == "wwm-uicons":
        errors.append("package.json name is still wwm-uicons")
    if errors:
        print("FAIL")
        for e in errors:
            print(" ", e)
        return 1
    print("ok", index_path.name, "keys", len(data), "pokemon", len(data.get("pokemon", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
