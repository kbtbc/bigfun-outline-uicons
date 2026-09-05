#!/usr/bin/env python3
"""Rebuild leftover 93×93 pokemon icons onto the locked 256 pipeline."""
from __future__ import annotations

import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enhance_all import load_indexes, resolve_pokemon, PX256_BY_NAME, UICONS_POKE
from rebuild_pokemon_256 import process, parse_aura, OUT_DIR

def loose_256(filename: str):
    m = UICONS_POKE.match(filename)
    if not m:
        return None, "unparsed"
    dex, b, e, f, c, g, a, s = m.groups()
    shiny = bool(s)
    d3 = f"{int(dex):03d}"
    shiny_s = "_shiny" if shiny else ""
    names = []
    if e == "1":
        names += [f"pokemon_icon_{d3}_51{shiny_s}.png", f"pokemon_icon_{d3}_51.png"]
    if e == "2":
        names += [f"pokemon_icon_{d3}_52{shiny_s}.png", f"pokemon_icon_{d3}_52.png"]
    if f and f.isdigit():
        fid = int(f)
        names.append(f"pokemon_icon_{d3}_{fid:02d}{shiny_s}.png")
        names.append(f"pokemon_icon_{d3}_{fid:02d}.png")
        names.append(f"pokemon_icon_{d3}_{10 + fid:02d}{shiny_s}.png")
        names.append(f"pokemon_icon_{d3}_{10 + fid:02d}.png")
    names += [
        f"pokemon_icon_{d3}_00{shiny_s}.png",
        f"pokemon_icon_{d3}_11{shiny_s}.png",
        f"pokemon_icon_{d3}_00.png",
        f"pokemon_icon_{d3}_11.png",
    ]
    for name in names:
        p = PX256_BY_NAME.get(name) or PX256_BY_NAME.get(name.lower())
        if p:
            return p, "256-loose"
    # any native 256 for this dex (prefer matching shiny)
    prefix = f"pokemon_icon_{d3}_"
    hits = []
    for name, p in PX256_BY_NAME.items():
        if not name.startswith(prefix) or not name.endswith(".png"):
            continue
        is_sh = "_shiny" in name
        if shiny and not is_sh:
            continue
        if (not shiny) and is_sh:
            continue
        hits.append((name, p))
    if not hits and shiny:
        for name, p in PX256_BY_NAME.items():
            if name.startswith(prefix) and name.endswith(".png") and "_shiny" not in name:
                hits.append((name, p))
    if hits:
        hits.sort(key=lambda x: x[0])
        return hits[0][1], "256-any"
    return None, "miss"


_READY = False

def worker(name: str):
    global _READY
    if not _READY:
        load_indexes()
        _READY = True
    aura = parse_aura(name)
    key = re.sub(r"_a[12]", "", name) if aura else name
    src, tag = resolve_pokemon(key)
    if src is None:
        src, tag = loose_256(key)
    if src is None:
        return name, "skip:no-pokeminers"
    try:
        out = process(Image.open(src), aura=aura if aura in (1, 2) else None)
        out.save(OUT_DIR / name, optimize=True)
        return name, f"ok:{tag}"
    except Exception as e:
        return name, f"err:{e}"


def main():
    load_indexes()
    leftovers = []
    for p in sorted(OUT_DIR.glob("*.png")):
        im = Image.open(p)
        if im.size != (256, 256):
            leftovers.append(p.name)
    print(f"leftovers {len(leftovers)}", flush=True)
    t0 = time.time()
    ok = skip = err = 0
    with ProcessPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(worker, n) for n in leftovers]
        for i, fut in enumerate(as_completed(futs), 1):
            name, status = fut.result()
            if status.startswith("ok"):
                ok += 1
            elif status.startswith("skip"):
                skip += 1
            else:
                err += 1
                print(name, status, flush=True)
            if i % 200 == 0 or i == len(leftovers):
                print(f"  {i}/{len(leftovers)} ok={ok} skip={skip} err={err} {time.time()-t0:.0f}s", flush=True)
    still = [p.name for p in OUT_DIR.glob("*.png") if Image.open(p).size != (256, 256)]
    print(f"done ok={ok} skip={skip} err={err} still_not_256={len(still)} {time.time()-t0:.0f}s", flush=True)
    if still[:10]:
        print("still", still[:10])


if __name__ == "__main__":
    main()
