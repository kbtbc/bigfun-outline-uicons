#!/usr/bin/env python3
"""Source-exhaustive audit (the reverse of audit_coverage.py).

audit_coverage walks the game master and asks "is there a file for everything
the master lists?". That direction cannot see art that rides no master field:
Gigantamax (bread flag), Primal (temp evo 4), and Urshifu's BREAD_DOUGH_MODE
tokens were all invisible to it (found 2026-09-05 via TiMXL cross-check).

This audit walks the other direction: every 256 source file PokeMiners ships
must be either used by some pack file or explained.

Pass 1: resolve every pack name to its source; anything unused is an orphan.
Pass 2: classify orphans by the UIcons name each would serve:
  portrait   .portrait. assets, not icons: excluded
  twin       the UIcons name ships from another source (numbered-first): fine
  REAL-GAP   mappable name missing from the pack: fail the audit
  unmapped   token this script cannot map without guessing: listed for a human
             (legacy numbered form slots ff=11..61 land here; their modern
             Addressable twins are covered by audit_coverage's master walk)

Usage: python tools/audit_sources.py     (exit 1 on any REAL-GAP)
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
POKEMON = ROOT / "pokemon"

sys.path.insert(0, str(TOOLS_DIR))
import rebuild_pokemon_256 as R

R._ensure_enhance()
import enhance_all as E

NUM = re.compile(r"^pokemon_icon_(\d{3})_(\d{2})(?:_(\d{2}))?(_shiny)?\.png$", re.I)


def main() -> int:
    E.load_indexes()
    existing = {p.name for p in POKEMON.glob("*.png")}
    token_to_cid = {v: k for k, v in E.COSTUME_BY_ID.items()}

    # ---- pass 1: which sources does the pack use? ----
    used: set[Path] = set()
    for p in sorted(POKEMON.glob("*.png")):
        name = p.name
        aura = R.parse_aura(name)
        key = re.sub(r"_a" + str(aura), "", name) if aura else name
        src, _tag = E.resolve_pokemon(key)
        if src is None and "_f" in key:
            # no-art forms are explicit base-art copies keyed on the base name
            src, _tag = E.resolve_pokemon(re.sub(r"_f\d+", "", key))
        if src is not None:
            used.add(src.resolve())

    all_srcs: dict[Path, str] = {}
    for name, path in E.PX256_BY_NAME.items():
        all_srcs.setdefault(Path(path).resolve(), name)
    orphans = sorted(all_srcs[s] for s in all_srcs if s not in used)

    # ---- pass 2: classify ----
    def costume_id(token: str):
        t = token.upper()
        return token_to_cid.get(t) or token_to_cid.get(t + "_NOEVOLVE") or (
            token_to_cid.get(t[: -len("_NOEVOLVE")]) if t.endswith("_NOEVOLVE") else None
        )

    def form_fid(dex: str, token: str):
        poke = E.MASTER["pokemon"].get(dex) or {}
        species = (poke.get("name") or "").upper().replace(" ", "_").replace("-", "_")
        cands = {token, f"{species}_{token}"}
        for alias, alts in getattr(E, "_FORM_ALIASES", {}).items():
            if alias == token:
                cands.update(alts)
        for fid, form in (poke.get("forms") or {}).items():
            if (form.get("proto") or "").upper() in cands:
                default = str(poke.get("default_form_id") or "")
                return None if str(fid) == default else str(fid)
        return "?"

    SPECIAL_F = {"GIGANTAMAX": "b2", "BREAD_DOUGH_MODE": "b2",
                 "BREAD_DOUGH_MODE_2": "b3", "MEGA": "e1", "MEGA_X": "e2",
                 "MEGA_Y": "e3", "PRIMAL": "e4"}

    twin = portrait = 0
    gaps: list[str] = []
    unmapped: list[str] = []
    for n in orphans:
        if ".portrait." in n.lower():
            portrait += 1
            continue
        uic = None
        m = E.ADDR_PARSE.match(n)
        if m:
            dex, ftok, ctok, g2 = m.group(1), m.group(2), m.group(3), m.group(4)
            shiny = ".s.icon" in n.lower()
            parts, ok = [str(int(dex))], True
            if ftok:
                t = ftok.upper()
                if t in SPECIAL_F:
                    parts.append(SPECIAL_F[t])
                else:
                    fid = form_fid(dex, t)
                    if fid == "?":
                        ok = False
                    elif fid:
                        parts.append(f"f{fid}")
            if ok and ctok:
                cid = costume_id(ctok)
                if cid is None:
                    ok = False
                else:
                    parts.append(f"c{cid}")
            if ok:
                if g2:
                    parts.append("g2")
                if shiny:
                    parts.append("s")
                uic = "_".join(parts) + ".png"
        else:
            nm = NUM.match(n)
            if nm:
                dex, ff, cc, sh = nm.groups()
                parts, ok = [str(int(dex))], True
                if ff == "01":
                    parts.append("g2")
                elif ff == "51":
                    parts.append("e1")
                elif ff == "52":
                    parts.append("e3")
                elif ff != "00":
                    ok = False  # legacy numbered form slot
                if ok and cc:
                    parts.append(f"c{int(cc)}")
                if ok:
                    if sh:
                        parts.append("s")
                    uic = "_".join(parts) + ".png"
        if uic is None:
            unmapped.append(n)
        elif uic in existing:
            twin += 1
        else:
            gaps.append(f"{uic}  <-  {n}")

    print(f"sources: {len(all_srcs)}  used: {len(used & set(all_srcs))}")
    print(f"portrait(excluded): {portrait}")
    print(f"twins(covered): {twin}")
    print(f"REAL-GAP: {len(gaps)}")
    for g in gaps[:60]:
        print("  ", g)
    print(f"unmapped(for a human): {len(unmapped)}")
    pats = Counter()
    for n in unmapped:
        nm = NUM.match(n)
        m = E.ADDR_PARSE.match(n)
        if nm:
            pats[f"numbered ff={nm.group(2)}"] += 1
        elif m and m.group(2):
            pats[f"addr f{m.group(2).upper()}"] += 1
        else:
            pats["other"] += 1
    for k, v in pats.most_common(25):
        print(f"   {k}: {v}")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
