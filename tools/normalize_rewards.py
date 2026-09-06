#!/usr/bin/env python3
"""Normalize reward icon fill so equal marker size means equal visual size.

Niantic's reward source art carries inconsistent padding (the Poke Ball filled
99% of its canvas while Great/Ultra filled 84%), so maps rendered them at
visibly different sizes. This tool contain-fits each icon's alpha bounding box
to a per-folder target max-extent, centered, aspect preserved, canvas size
unchanged.

Locked targets (Kelly, 2026-09-06): items, candy, XL candy and coins sit at
0.85 (round objects read optically larger, and stacked-amount `_a` variants
need edge room); mega resources, stardust and XP fill the canvas at 0.99.

Do NOT add gym (size encodes trainer occupancy), weather (intentional
composition), raid/egg (glow auras inflate the bbox) or misc (heterogeneous
symbols) to the target table.

Idempotent: files already within 0.015 of target are left untouched, so
re-running never re-encodes the whole set. `0.png` (unmatched placeholder) is
always skipped.

Usage: python tools/normalize_rewards.py
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

TARGETS = {
    "reward/item": 0.85,
    "reward/candy": 0.85,
    "reward/xl_candy": 0.85,
    "reward/pokecoin": 0.85,
    "reward/mega_resource": 0.99,
    "reward/stardust": 0.99,
    "reward/experience": 0.99,
}

# Crop threshold 2, not the pipeline's 20: items carry faint glows whose edge
# alpha drifts below 20 after a LANCZOS pass, which made re-runs oscillate
# (shrink, remeasure, regrow). Threshold 2 keeps all visible content inside the
# box so the measurement is stable across encodes.
SIL_THR = 2
TOLERANCE = 0.02


def normalize(p: Path, target: float) -> bool:
    im = Image.open(p).convert("RGBA")
    a = np.asarray(im)[..., 3]
    ys, xs = np.where(a > SIL_THR)
    if len(xs) == 0:
        return False
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    w, h = x1 - x0, y1 - y0
    extent = max(w / im.width, h / im.height)
    if abs(extent - target) < TOLERANCE:
        return False
    # Scale so the max extent (relative to a possibly non-square canvas) hits
    # the target exactly; scaling one axis by target*W/w overshoots the other
    # axis on non-square canvases (found on the 185x193 ball icons).
    scale = target / extent
    nw = max(1, round(w * scale))
    nh = max(1, round(h * scale))
    crop = im.crop((x0, y0, x1, y1)).resize((nw, nh), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(crop, ((im.width - nw) // 2, (im.height - nh) // 2), crop)
    # Windows AV/indexer can briefly lock freshly written files (OSError 22);
    # retry a few times before giving up.
    for attempt in range(4):
        try:
            out.save(p)
            break
        except OSError:
            if attempt == 3:
                raise
            time.sleep(0.5)
    return True


def main() -> int:
    total = 0
    for rel, target in TARGETS.items():
        d = ROOT / rel
        changed = files = 0
        for p in sorted(d.glob("*.png")):
            if p.name == "0.png":
                continue
            files += 1
            if normalize(p, target):
                changed += 1
        total += changed
        print(f"{rel}: {changed}/{files} normalized to {target}")
    print(f"total changed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
