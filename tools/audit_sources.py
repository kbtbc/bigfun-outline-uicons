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
  legacy-slot  numbered form slots (ff >= 11) PokeMiners keeps from older game
             versions: older renders of forms the pack already builds from modern
             art. Covered when a species has no more distinct slots than real-art
             pack forms plus the default form (checked 2026-11-17: exactly one
             more for all 25 multi-form species). A slot that carries a costume
             id is covered only if the pack has that costume for the species.
  reviewed   listed in tools/audit-reviewed.json: a person compared the file by
             image and found it covered. Never add a file only to quiet the audit.
  unmapped   anything else this script cannot map without guessing: listed for
             a human. Each entry here needs a decision.

Usage: python tools/audit_sources.py     (exit 1 on any REAL-GAP)
"""
from __future__ import annotations

import json
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
FORM_RE = re.compile(r"^(\d+)(?:_[be]\d+)*_f(\d+)")
COSTUME_RE = re.compile(r"^(\d+)(?:_[bef]\d+)*_c(\d+)")
LEGACY_MIN_FF = 11  # 00 base, 01 female, 51/52 Mega are mapped below; 11+ are legacy form slots
REVIEWED = TOOLS_DIR / "audit-reviewed.json"


def load_reviewed() -> dict[str, str]:
    try:
        return json.loads(REVIEWED.read_text(encoding="utf-8")).get("names", {})
    except FileNotFoundError:
        return {}


def main() -> int:
    E.load_indexes()
    existing = {p.name for p in POKEMON.glob("*.png")}
    token_to_cid = {v: k for k, v in E.COSTUME_BY_ID.items()}

    # ---- pass 1: which sources does the pack use? ----
    used: set[Path] = set()
    real_forms: dict[str, set[str]] = {}  # dex -> form ids built from art of their own
    pack_costumes: dict[str, set[str]] = {}  # dex -> costume ids the pack ships
    reviewed = load_reviewed()
    for name in existing:
        cm = COSTUME_RE.match(name)
        if cm:
            pack_costumes.setdefault(str(int(cm.group(1))), set()).add(str(int(cm.group(2))))
    for p in sorted(POKEMON.glob("*.png")):
        name = p.name
        aura = R.parse_aura(name)
        key = re.sub(r"_a" + str(aura), "", name) if aura else name
        src, _tag = E.resolve_pokemon(key)
        fm = FORM_RE.match(key)
        if src is not None and fm:
            real_forms.setdefault(str(int(fm.group(1))), set()).add(fm.group(2))
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
    legacy: dict[str, list[str]] = {}  # dex -> legacy numbered slot files, judged below
    reviewed_hit: list[str] = []
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
            nm = NUM.match(n)
            if nm and int(nm.group(2)) >= LEGACY_MIN_FF:
                legacy.setdefault(str(int(nm.group(1))), []).append(n)
            elif n in reviewed:
                reviewed_hit.append(n)
            else:
                unmapped.append(n)
        elif uic in existing:
            twin += 1
        else:
            gaps.append(f"{uic}  <-  {n}")

    # Legacy numbered slots: covered when the species has no more distinct slots than
    # real-art pack forms plus the default form, and a costume slot has its costume.
    legacy_ok: list[str] = []
    for dex, files in sorted(legacy.items(), key=lambda kv: int(kv[0])):
        slots = {NUM.match(f).group(2) for f in files}
        room = len(real_forms.get(dex, set())) + 1
        for f in files:
            cc = NUM.match(f).group(3)
            costume_ok = cc is None or str(int(cc)) in pack_costumes.get(dex, set())
            if len(slots) <= room and costume_ok:
                legacy_ok.append(f)
            else:
                unmapped.append(f)
    unmapped.sort()
    stale = sorted(set(reviewed) - set(orphans))

    print(f"sources: {len(all_srcs)}  used: {len(used & set(all_srcs))}")
    print(f"portrait(excluded): {portrait}")
    print(f"twins(covered): {twin}")
    print(f"legacy numbered slots(covered): {len(legacy_ok)}  "
          f"species: {len({str(int(NUM.match(f).group(1))) for f in legacy_ok})}")
    print(f"reviewed(covered, tools/audit-reviewed.json): {len(reviewed_hit)}")
    if stale:
        print(f"reviewed entries no longer orphaned (remove from the file): {len(stale)}")
    print(f"REAL-GAP: {len(gaps)}")
    for g in gaps[:60]:
        print("  ", g)
    print(f"unmapped(for a human): {len(unmapped)}")
    for n in unmapped[:60]:
        print("  ", n)
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
