#!/usr/bin/env python3
"""Verify the distance-protected wing zone is untouched by the aa_in prototype.

For every golden file, pixels whose distance from the opaque core exceeds the
ramp band (cut_px + aa_in, plus blur margin) and that are mid-alpha in live B1
must be byte-identical between live B1 and the aa_in output, and their hue
(INV-3, measured on the wing zone only) must not drift.
"""
from __future__ import annotations

import colorsys
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
from rebuild_pokemon_256 import edt_outside, SOLID_THR  # noqa: E402

names = [
    l.strip()
    for l in (REPO / "scripts" / "golden.txt").read_text().splitlines()
    if l.strip() and not l.startswith("#")
]


def hue_med(arr: np.ndarray, mask: np.ndarray) -> float:
    px = arr[mask].astype(np.float32)
    if len(px) == 0:
        return -1.0
    st = np.clip(px[:, :3] / np.maximum(px[:, 3:4] / 255.0, 1e-3), 0, 255) / 255.0
    hs = [
        colorsys.rgb_to_hsv(*p)[0] * 360
        for p in st[:: max(1, len(st) // 1500)]
        if colorsys.rgb_to_hsv(*p)[1] > 0.15
    ]
    return float(np.median(hs)) if hs else -1.0


print(f"{'file':16s} {'far px':>8s} {'maxdiff':>8s} {'hue drift':>10s}")
worst = 0
for n in names:
    b1 = np.array(Image.open(REPO / "pokemon" / n).convert("RGBA")).astype(np.int16)
    aa = np.array(Image.open(REPO / "docs/qa/fable_aain" / n).convert("RGBA")).astype(np.int16)
    solid = b1[:, :, 3] >= SOLID_THR
    d = edt_outside(solid)
    far = (d > 2.85) & (b1[:, :, 3] > 20) & (b1[:, :, 3] < 200)
    diff = int(np.abs(b1 - aa)[far].max()) if far.any() else 0
    hb, ha = hue_med(b1, far), hue_med(aa, far)
    dh = min(abs(ha - hb), 360 - abs(ha - hb)) if hb >= 0 and ha >= 0 else 0.0
    worst = max(worst, diff)
    print(f"{n:16s} {int(far.sum()):8d} {diff:8d} {dh:10.2f}")
print("wing zone:", "UNTOUCHED" if worst == 0 else f"CHANGED (max diff {worst})")
