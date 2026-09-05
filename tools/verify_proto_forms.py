#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image
import numpy as np

from _paths import REPO_ROOT

OUT = REPO_ROOT / "pokemon"

def analyze(name):
    p = OUT / name
    if not p.exists():
        return {"name": name, "exists": False}
    im = Image.open(p).convert("RGBA")
    a = np.array(im)
    alpha = a[:,:,3]
    h, w = alpha.shape
    opaque = alpha > 10
    fill = opaque.mean()
    rows = np.any(opaque, axis=1)
    cols = np.any(opaque, axis=0)
    if not rows.any():
        pad = None
    else:
        top = int(np.argmax(rows))
        bottom = int(h - 1 - np.argmax(rows[::-1]))
        left = int(np.argmax(cols))
        right = int(w - 1 - np.argmax(cols[::-1]))
        pad = min(top, bottom, left, right)
    if opaque.any():
        rgb = a[:,:,:3][opaque].mean(axis=0)
    else:
        rgb = (0,0,0)
    purple = None
    purple_count = 0
    if "_a1" in name:
        r,g,b = a[:,:,0], a[:,:,1], a[:,:,2]
        mid = (alpha > 20) & (alpha < 220)
        purp = mid & (b.astype(int) > g.astype(int) + 20) & (r.astype(int) > g.astype(int) + 10) & (b.astype(int) > 80)
        purple = float(purp.mean()) if mid.any() else 0.0
        purple_count = int(purp.sum())
    return {
        "name": name, "exists": True, "size": (w,h),
        "fill": round(float(fill), 4), "min_pad": pad,
        "mean_rgb": tuple(round(float(x),1) for x in rgb),
        "purple_frac": purple, "purple_count": purple_count,
    }

from enhance_all import load_indexes, resolve_pokemon
load_indexes()

def resolve(n):
    src, tag = resolve_pokemon(n)
    return str(src) if src else None, tag

checks = ["201_f1.png", "201_f1_a1.png", "412.png", "412_f119.png", "412_f120.png", "0.png"]
for n in checks:
    info = analyze(n)
    src, tag = resolve(n)
    print(n, info, "src=", src, "tag=", tag)

print("\n--- Burmy color distinctness ---")
burmy = [analyze(n) for n in ["412.png", "412_f119.png", "412_f120.png"]]
rgbs = [b["mean_rgb"] for b in burmy]
print("rgbs:", rgbs)
for i in range(3):
    for j in range(i+1,3):
        d = sum((rgbs[i][k]-rgbs[j][k])**2 for k in range(3))**0.5
        print(f"  dist {burmy[i]['name']} vs {burmy[j]['name']}: {d:.1f}")

print("\n--- 0.png unmatched ---")
src0, tag0 = resolve("0.png")
print("0.png src=", src0, "tag=", tag0)
zeros = sorted(OUT.glob("0*.png"))
print(f"0_* count: {len(zeros)}")
for z in zeros[:30]:
    s,t = resolve(z.name)
    print(z.name, "tag=", t, "src=", s)
