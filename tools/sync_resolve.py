#!/usr/bin/env python3
"""Detect and rebuild pack files whose resolved source changed.

Why: a form can enter the game master before its art ships (Pikachu Glass
Helmet 2026, master form 3357). Policy builds it as a base-art copy so maps
show something correct. When PokeMiners later ships the real texture, the
name resolves to different art, but the file already exists, so the watcher
skips it and the audits see the name as covered. This tool closes that hole.

tools/resolve-manifest.json records, for every pack file, the source basename
and tag it was built from. Each run re-resolves every name, rebuilds any file
whose source changed, and rewrites the manifest.

Usage:
  python tools/sync_resolve.py            # report drift only
  python tools/sync_resolve.py --build    # rebuild drifted files + manifest
  python tools/sync_resolve.py --init     # write manifest from current state

Exit code: 0 = no drift, 2 = drift found (and rebuilt with --build).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
POKEMON = ROOT / "pokemon"
MANIFEST = TOOLS_DIR / "resolve-manifest.json"

sys.path.insert(0, str(TOOLS_DIR))
import rebuild_pokemon_256 as R

R._ensure_enhance()
import enhance_all as E


def current_state() -> dict[str, list]:
    E.load_indexes()
    state: dict[str, list] = {}
    for p in sorted(POKEMON.glob("*.png")):
        name = p.name
        aura = R.parse_aura(name)
        key = re.sub(r"_a" + str(aura), "", name) if aura else name
        src, tag = E.resolve_pokemon(key)
        if src is None and "_f" in key:
            # no-art form: explicit base-art copy keyed on the base name
            src, tag = E.resolve_pokemon(re.sub(r"_f\d+", "", key))
            tag = f"base-copy:{tag}"
        state[name] = [src.name if src else None, tag]
    return state


def main() -> int:
    build = "--build" in sys.argv
    init = "--init" in sys.argv
    state = current_state()

    if init or not MANIFEST.exists():
        MANIFEST.write_text(
            json.dumps(state, indent=0, sort_keys=True), encoding="utf-8"
        )
        print(f"manifest written: {len(state)} entries -> {MANIFEST.name}")
        return 0

    old = json.loads(MANIFEST.read_text(encoding="utf-8"))
    drift = sorted(n for n in state if old.get(n) and old[n] != state[n])
    new_names = sorted(n for n in state if n not in old)
    print(f"files: {len(state)}  drift: {len(drift)}  new: {len(new_names)}")
    for n in drift[:40]:
        print(f"  {n}: {old[n][0]} -> {state[n][0]}")
    if len(drift) > 40:
        print(f"  ... and {len(drift) - 40} more")

    if drift and build:
        ok = err = 0
        for n in drift:
            key = None
            if state[n][1].startswith("base-copy:"):
                aura = R.parse_aura(n)
                key = re.sub(r"_f\d+", "", n)
                if aura:
                    key = re.sub(r"_a" + str(aura), "", key)
            _name, status = R.worker(n, key=key)
            if status.startswith("ok"):
                ok += 1
            else:
                err += 1
                print("ERR", n, status)
        print(f"rebuilt ok={ok} err={err}")
    if (drift and build) or new_names or init:
        MANIFEST.write_text(
            json.dumps(state, indent=0, sort_keys=True), encoding="utf-8"
        )
        print("manifest updated")
    return 2 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
