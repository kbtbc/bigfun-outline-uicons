#!/usr/bin/env python3
"""Weekly PokeMiners watcher: find and build newly added Pokemon.

Detects, against the current pack in pokemon/:
  1. New base dex: the game master lists the species, PokeMiners has GO 256 art
     (numbered or 256 Addressable), and pokemon/{dex}.png does not exist.
  2. New forms: every non-default master form (default forms and
     _NORMAL/_STANDARD aliases are covered by the base file, so skipped).
     Forms with their own art build from it; forms without art of their own
     build as explicit base-art copies (Kelly policy 2026-09-05: every form
     gets a file so maps can tell Spinda patterns / Scatterbug regions apart).
  3. New female art: a numbered _01 slot or bare Addressable .g2 with no
     pack {dex}_g2.png. (Form/costume+female combos are audit_coverage.py's
     job; run it alongside this watcher.)

For every new name it builds the standard variant family through the locked
pipeline: base, _s (only when shiny source art resolves), _a1, _a1_s, _a2,
_a2_s.

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

import re
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

    # name -> resolver key override (None = resolve by own name;
    # base-art copies resolve by the name with the _f flag stripped)
    new_names: dict[str, str | None] = {}
    for dex, poke in (E.MASTER.get("pokemon") or {}).items():
        dex = str(dex)
        if dex not in have_art:
            continue  # no GO art: Home-only / unreleased, out of scope
        if f"{dex}.png" not in existing:
            new_names[f"{dex}.png"] = None
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
            # Form with its own art builds from it. Form without art of its
            # own (resolver miss) builds as an explicit base-art copy, keyed
            # on the base name, so long as the base resolves.
            src, _tag = E.resolve_pokemon(fname)
            if src is not None:
                new_names[fname] = None
            elif E.resolve_pokemon(f"{dex}.png")[0] is not None:
                new_names[fname] = f"{dex}.png"

    # New female art: numbered _01 slot or bare Addressable pm{dex}.g2.
    for name in E.PX256_BY_NAME:
        gdex: str | None = None
        nm = re.match(r"^pokemon_icon_(\d{3})_01\.png$", name)
        if nm:
            gdex = str(int(nm.group(1)))
        else:
            m = E.ADDR_PARSE.match(name)
            if m and m.group(4) and not m.group(2) and not m.group(3) and ".s.icon" not in name:
                gdex = m.group(1)
        if gdex is not None and f"{gdex}_g2.png" not in existing:
            new_names[f"{gdex}_g2.png"] = None

    built: list[str] = []
    skipped: list[str] = []
    needs_review: list[str] = []
    for name in sorted(new_names):
        key = new_names[name]
        stem, kstem = name[:-4], (key[:-4] if key else name[:-4])
        # Shiny availability gates every _s variant, checked on the resolve key.
        has_shiny = E.resolve_pokemon(f"{kstem}_s.png")[0] is not None
        family: list[tuple[str, str | None]] = [(name, key)]
        for suffix in ("_s", "_a1", "_a1_s", "_a2", "_a2_s"):
            variant = f"{stem}{suffix}.png"
            if variant in existing:
                continue
            if suffix.endswith("_s") and not has_shiny:
                skipped.append(f"{variant} (no shiny source)")
                continue
            family.append((variant, f"{kstem}{suffix}.png" if key else None))
        for fname, fkey in family:
            if build:
                _n, status = R.worker(fname, key=fkey)
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
