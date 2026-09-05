#!/usr/bin/env python3
"""Weekly PokeMiners watcher: find and build newly added Pokemon.

Detects, against the current pack in pokemon/:
  1. New base dex: the game master lists the species, PokeMiners has GO 256 art
     (numbered or 256 Addressable), and pokemon/{dex}.png does not exist.
  2. New forms: the form's proto resolves to PokeMiners art and
     pokemon/{dex}_f{fid}.png does not exist (default forms and
     _NORMAL/_STANDARD aliases are covered by the base file, so skipped).

For every new name it builds the standard variant family through the locked
pipeline: base, _s (only when shiny source art resolves), _a1, _a2.

Never guesses: only names whose source resolves through enhance_all's
resolve_pokemon are built. Anything that errors is listed under NEEDS-REVIEW
for a human; nothing is substituted.

Usage:
  python tools/check_new_pokemon.py            # report only
  python tools/check_new_pokemon.py --build    # build missing icons into pokemon/

Requires POGO_ASSETS and MASTER_JSON env (same as rebuild_pokemon_256.py).
Exit code: 0 = nothing new, 2 = new icons found (and built with --build).
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
POKEMON = ROOT / "pokemon"

sys.path.insert(0, str(TOOLS_DIR))
import rebuild_pokemon_256 as R  # noqa: E402

R._ensure_enhance()
import enhance_all as E  # noqa: E402


def main() -> int:
    build = "--build" in sys.argv
    E.load_indexes()

    existing = {p.name for p in POKEMON.glob("*.png")}

    # Which dex have any GO 256 art at all? (numbered or 256 Addressable;
    # PX256_BY_NAME rglobs the 256 folder so it includes Addressable Assets.)
    have_art: set[str] = set()
    for name in E.PX256_BY_NAME:
        if name.startswith("pokemon_icon_"):
            try:
                have_art.add(str(int(name.split("_")[2])))
            except (IndexError, ValueError):
                pass
        m = E.ADDR_PARSE.match(name)
        if m:
            have_art.add(m.group(1))

    new_names: list[str] = []
    for dex, poke in (E.MASTER.get("pokemon") or {}).items():
        dex = str(dex)
        if dex not in have_art:
            continue  # no GO art: Home-only / unreleased, out of scope
        if f"{dex}.png" not in existing:
            new_names.append(f"{dex}.png")
        default_fid = str(poke.get("default_form_id") or "")
        for fid, form in (poke.get("forms") or {}).items():
            fid = str(fid)
            if fid == default_fid:
                continue
            proto = (form.get("proto") or "").upper()
            if not proto or proto.endswith("_NORMAL") or proto.endswith("_STANDARD"):
                continue
            fname = f"{dex}_f{fid}.png"
            if fname in existing:
                continue
            # Hard rule: a form must never silently fall back to the default
            # species art. resolve_pokemon returns the base sprite when it
            # finds no form-specific art, so only treat the form as new when
            # its resolved source differs from the base resolve. Same-art
            # forms are covered by the base file (Burmy-alias convention).
            src, _tag = E.resolve_pokemon(fname)
            base_src, _bt = E.resolve_pokemon(f"{dex}.png")
            if src is not None and src != base_src:
                new_names.append(fname)

    built: list[str] = []
    skipped: list[str] = []
    needs_review: list[str] = []
    for name in sorted(new_names):
        stem = name[:-4]
        family = [name]
        for suffix in ("_s", "_a1", "_a2"):
            variant = f"{stem}{suffix}.png"
            if variant in existing:
                continue
            if suffix == "_s":
                src, _tag = E.resolve_pokemon(variant)
                if src is None:
                    skipped.append(f"{variant} (no shiny source)")
                    continue
            family.append(variant)
        for fname in family:
            if build:
                _n, status = R.worker(fname)
                if status.startswith("ok"):
                    built.append(fname)
                else:
                    needs_review.append(f"{fname} ({status})")
            else:
                built.append(fname)

    print(f"pack files: {len(existing)}")
    print(f"new icons {'built' if build else 'found'}: {len(built)}")
    for n in built:
        print("  +", n)
    if skipped:
        print(f"skipped (expected): {len(skipped)}")
        for n in skipped:
            print("  ~", n)
    if needs_review:
        print(f"NEEDS-REVIEW: {len(needs_review)}")
        for n in needs_review:
            print("  ?", n)
    return 2 if built or needs_review else 0


if __name__ == "__main__":
    sys.exit(main())
