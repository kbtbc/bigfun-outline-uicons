#!/usr/bin/env python3
from PIL import Image
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import REPO_ROOT
d = REPO_ROOT / "pokemon"
non = []
for p in d.glob("*.png"):
    im = Image.open(p)
    if im.size != (256, 256):
        non.append((p.name, im.size))
print("total", sum(1 for _ in d.glob("*.png")))
print("non256", len(non))
if non[:30]:
    print("sample_non256", non[:30])

def fill_pad(name):
    im = Image.open(d / name).convert("RGBA")
    a = np.array(im)[:, :, 3]
    ys, xs = np.where(a > 20)
    if len(xs) == 0:
        print(name, "EMPTY")
        return
    top, bottom = int(ys.min()), int(ys.max())
    left, right = int(xs.min()), int(xs.max())
    w = right - left + 1
    h = bottom - top + 1
    fill = max(w, h) / 256.0
    min_pad = min(left, top, 255 - right, 255 - bottom)
    print(f"{name}: fill={fill:.4f} min_pad={min_pad} bbox=({left},{top})-({right},{bottom}) dim={w}x{h}")

for n in ["686.png", "25.png", "519.png", "582.png"]:
    fill_pad(n)
