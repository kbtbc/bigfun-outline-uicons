#!/usr/bin/env python3
"""Convert the pack to lossless WebP in place (for the bigfun-webp-outline branch).

Walks every pack folder (everything except tools, docs, dotdirs, node_modules),
re-encodes each .png as lossless .webp with the same basename, and deletes the
.png. Lossless means pixel-identical to the PNG pack; only the container
changes. Run index.js afterwards to regenerate index.json with .webp names.

Usage: python tools/export_webp.py [--workers N]
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"tools", "docs", "node_modules", ".git", ".github", ".cursor", ".cache"}


def convert(png: Path) -> tuple[str, str]:
    from PIL import Image

    try:
        im = Image.open(png)
        im.load()
        if im.mode not in ("RGBA", "RGB"):
            im = im.convert("RGBA")
        out = png.with_suffix(".webp")
        im.save(out, "WEBP", lossless=True, quality=100, method=6)
        png.unlink()
        return png.name, "ok"
    except Exception as e:  # report, never silently drop an icon
        return png.name, f"err:{e}"


def main() -> int:
    workers = 4
    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])
    pngs = [
        p
        for p in ROOT.rglob("*.png")
        if not any(part in SKIP for part in p.relative_to(ROOT).parts)
    ]
    print(f"converting {len(pngs)} png -> lossless webp ({workers} workers)", flush=True)
    t0 = time.time()
    ok = err = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(convert, p) for p in pngs]
        for i, fut in enumerate(as_completed(futs), 1):
            name, status = fut.result()
            if status == "ok":
                ok += 1
            else:
                err += 1
                print(name, status, flush=True)
            if i % 2000 == 0 or i == len(pngs):
                print(f"  {i}/{len(pngs)} ok={ok} err={err} {time.time()-t0:.0f}s", flush=True)
    print(f"done ok={ok} err={err} in {time.time()-t0:.0f}s", flush=True)
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
