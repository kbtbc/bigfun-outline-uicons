#!/usr/bin/env python3
"""Global coverage audit: forms, costumes, gender variants, shinies.

For every species in the game master that has GO art, checks that every
variant with PokeMiners art has a pack file, and that every requested variant
resolves to variant-specific art (not silently to base).

Categories reported:
  MISSING-FORM      master form with distinct art, no pack file
  NOART-FORM        master form with no art of its own (candidate for an
                    explicit base-art copy, Kelly policy 2026-09-05)
  MISSING-COSTUME   PokeMiners costume art with no pack _c file
  MISSING-GENDER    Addressable .g2 art with no pack _g2 file
  MISSING-SHINY     shiny art exists, no _s pack file for an existing name
  WRONG-ART         existing pack name whose resolve returns base art while
                    variant art exists (resolver bug indicator)
  NEEDS-MAPPING     source art whose token cannot be mapped without guessing

Usage:
  python tools/audit_coverage.py                 # report to stdout
  python tools/audit_coverage.py --plan out.json # also write a build plan
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
POKEMON = ROOT / "pokemon"

sys.path.insert(0, str(TOOLS_DIR))
import rebuild_pokemon_256 as R

R._ensure_enhance()
import enhance_all as E

NUM_COSTUME = re.compile(r"^pokemon_icon_(\d{3})_(\d{2})_(\d{2})(_shiny)?\.png$")


def main() -> int:
    E.load_indexes()
    existing = {p.name for p in POKEMON.glob("*.png")}
    token_to_cid = {v: k for k, v in E.COSTUME_BY_ID.items()}

    # Dex with any GO art (numbered or 256 Addressable).
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

    missing_form: list[str] = []
    noart_form: list[str] = []
    missing_costume: list[str] = []
    missing_gender: list[str] = []
    missing_shiny: list[str] = []
    wrong_art: list[str] = []
    needs_mapping: list[str] = []

    base_src_cache: dict[str, object] = {}

    def base_src(dex: str):
        if dex not in base_src_cache:
            base_src_cache[dex] = E.resolve_pokemon(f"{dex}.png")[0]
        return base_src_cache[dex]

    # ---- forms (regionals are forms too) ----
    for dex, poke in (E.MASTER.get("pokemon") or {}).items():
        dex = str(dex)
        if dex not in have_art:
            continue
        default_fid = str(poke.get("default_form_id") or "")
        for fid, form in (poke.get("forms") or {}).items():
            fid = str(fid)
            if fid == default_fid:
                continue
            proto = (form.get("proto") or "").upper()
            if not proto or proto.endswith("_NORMAL") or proto.endswith("_STANDARD"):
                continue
            fname = f"{dex}_f{fid}.png"
            src, _tag = E.resolve_pokemon(fname)
            if src is None:
                if fname not in existing:
                    noart_form.append(f"{fname} ({proto})")
                continue
            if src == base_src(dex):
                # resolver returned base art for an explicit form request
                wrong_art.append(f"{fname} ({proto}) -> base art")
                continue
            if fname not in existing:
                missing_form.append(f"{fname} ({proto})")
            else:
                # file exists; confirm the shipped bytes came from form art is
                # covered by the resolve-diff rebuild, not re-checked here
                pass

    # ---- costumes ----
    # numbered: pokemon_icon_{ddd}_{ff}_{cc}.png, cc == UIcons costume id
    seen_costumes: set[tuple[str, int]] = set()
    for name in E.PX256_BY_NAME:
        m = NUM_COSTUME.match(name)
        if m and not m.group(4) and m.group(2) == "00":
            # Form+costume combos (slot != 00) use legacy numbered form ids we
            # cannot map without guessing; their Addressable twins cover them.
            dex = str(int(m.group(1)))
            cid = int(m.group(3))
            seen_costumes.add((dex, cid))
    # addressable: pm{dex}[.f{FORM}].c{TOKEN}
    # Costume art can be form-specific (Galarian Ponyta GO Fest 2021), in
    # which case the UIcons name carries both flags: {dex}_f{fid}_c{cid}.png.
    def costume_id(token: str) -> int | None:
        # Sources sometimes drop the documented _NOEVOLVE suffix.
        return token_to_cid.get(token) or token_to_cid.get(token + "_NOEVOLVE")

    def form_fid(dex: str, token: str) -> str | None:
        poke = E.MASTER["pokemon"].get(dex) or {}
        species = (poke.get("name") or "").upper().replace(" ", "_").replace("-", "_")
        cands = {token, f"{species}_{token}"}
        for alias in E._FORM_ALIASES.get(token, []):
            cands.update({alias, f"{species}_{alias}"})
        for fid, form in (poke.get("forms") or {}).items():
            if (form.get("proto") or "").upper() in cands:
                return str(fid)
        return None

    seen_form_costumes: set[tuple[str, str, int]] = set()
    for name in E.PX256_BY_NAME:
        m = E.ADDR_PARSE.match(name)
        if not m or not m.group(3) or ".s.icon" in name:
            continue
        dex, ftoken, ctoken = m.group(1), m.group(2), m.group(3).upper()
        cid = costume_id(ctoken)
        if cid is None:
            needs_mapping.append(f"pm{dex}.c{ctoken} (no UIcons costume id)")
            continue
        if ftoken:
            fid = form_fid(dex, ftoken.upper())
            if fid is None:
                needs_mapping.append(f"pm{dex}.f{ftoken}.c{ctoken} (no master form id)")
            else:
                seen_form_costumes.add((dex, fid, cid))
        else:
            seen_costumes.add((dex, cid))
    for dex, cid in sorted(seen_costumes, key=lambda t: (int(t[0]), t[1])):
        fname = f"{dex}_c{cid}.png"
        if fname not in existing:
            src, _tag = E.resolve_pokemon(fname)
            if src is not None and src != base_src(dex):
                missing_costume.append(fname)
            elif src is None:
                needs_mapping.append(f"{fname} (art seen, resolver miss)")
    for dex, fid, cid in sorted(seen_form_costumes, key=lambda t: (int(t[0]), int(t[1]), t[2])):
        fname = f"{dex}_f{fid}_c{cid}.png"
        if fname not in existing:
            src, _tag = E.resolve_pokemon(fname)
            if src is not None:
                missing_costume.append(fname)
            else:
                needs_mapping.append(f"{fname} (art seen, resolver miss)")

    # ---- gender: every place female art lives ----
    # 1. bare Addressable pm{dex}.g2
    # 2. numbered female slot pokemon_icon_{ddd}_01.png (older gens)
    # 3. form/costume + .g2 combos (mapped, never guessed)
    female_expect: set[str] = set()
    for name in sorted(E.PX256_BY_NAME):
        m = E.ADDR_PARSE.match(name)
        if m and m.group(4) and ".s.icon" not in name:
            dex, ftoken, ctoken = m.group(1), m.group(2), m.group(3)
            parts = [dex]
            if ftoken:
                fid = form_fid(dex, ftoken.upper())
                if fid is None:
                    needs_mapping.append(f"pm{dex}.f{ftoken}.g2 (no master form id)")
                    continue
                parts.append(f"f{fid}")
            if ctoken:
                cid = costume_id(ctoken.upper())
                if cid is None:
                    needs_mapping.append(f"pm{dex}.c{ctoken}.g2 (no UIcons costume id)")
                    continue
                parts.append(f"c{cid}")
            female_expect.add("_".join(parts) + "_g2.png")
        nm = re.match(r"^pokemon_icon_(\d{3})_01\.png$", name)
        if nm:
            female_expect.add(f"{int(nm.group(1))}_g2.png")
    for fname in sorted(female_expect):
        dex = fname.split("_", 1)[0]
        src, _tag = E.resolve_pokemon(fname)
        if src is not None and src == base_src(dex):
            wrong_art.append(f"{fname} -> base art while female art exists")
        if fname not in existing:
            missing_gender.append(fname)

    # ---- shinies for existing base names ----
    for name in sorted(existing):
        if name.endswith("_s.png") or "_a1" in name or "_a2" in name:
            continue
        sname = name[:-4] + "_s.png"
        if sname in existing:
            continue
        src, _tag = E.resolve_pokemon(sname)
        if src is not None and src != E.resolve_pokemon(name)[0]:
            missing_shiny.append(sname)

    report = {
        "MISSING-FORM": missing_form,
        "NOART-FORM": noart_form,
        "MISSING-COSTUME": missing_costume,
        "MISSING-GENDER": missing_gender,
        "MISSING-SHINY": missing_shiny,
        "WRONG-ART": wrong_art,
        "NEEDS-MAPPING": sorted(set(needs_mapping)),
    }
    for cat, items in report.items():
        print(f"{cat}: {len(items)}")
        for it in items[:40]:
            print("  ", it)
        if len(items) > 40:
            print(f"   ... and {len(items) - 40} more")

    if "--plan" in sys.argv:
        dest = Path(sys.argv[sys.argv.index("--plan") + 1])
        dest.write_text(json.dumps(report, indent=1), encoding="utf-8")
        print("plan ->", dest)
    return 0


if __name__ == "__main__":
    main()
