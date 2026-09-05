#!/usr/bin/env python3
"""QA sheets + invariants for the golden set (agent-fable worktree).

Sheets (written to docs/qa/sheets/, prefix fable_):
  fable_mapsize_light/dark    ~48px: TiMXL / live B1 / aa_in prototype
  fable_canvas256_light/dark  full 256 canvas, same three rows (TiMXL 93 centered, not upscaled)
  fable_zoom3x_inner          3x nearest crop at the top body/stroke join, B1 vs aa_in, light bg

Checks printed to stdout:
  INV-1  mid-alpha pixel count aa_in vs live B1 (wings must not black)
  INV-3  mean hue of translucent region aa_in vs live B1 (<= 10 degrees)
  _a1    opaque-extent bbox (alpha >= 250) B1 vs aa_in
"""
from __future__ import annotations

import colorsys
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
LIVE = REPO / "pokemon"
AAIN = REPO / "docs" / "qa" / "fable_aain"
TIMXL = REPO / ".cache" / "timxl" / "pokemon"
SHEETS = REPO / "docs" / "qa" / "sheets"

LIGHT = (242, 239, 233, 255)
DARK = (43, 43, 51, 255)
FONT = ImageFont.load_default()

names = [
    l.strip()
    for l in (REPO / "scripts" / "golden.txt").read_text().splitlines()
    if l.strip() and not l.startswith("#")
]


def load(folder: Path, name: str) -> Image.Image | None:
    p = folder / name
    return Image.open(p).convert("RGBA") if p.exists() else None


def cell(im: Image.Image | None, size: int, icon: int, bg) -> Image.Image:
    """Icon contain-fit to `icon` px (only downscale), centered on a size-px tile."""
    tile = Image.new("RGBA", (size, size), bg)
    if im is None:
        d = ImageDraw.Draw(tile)
        d.line((8, 8, size - 8, size - 8), fill=(200, 60, 60, 255), width=2)
        d.line((size - 8, 8, 8, size - 8), fill=(200, 60, 60, 255), width=2)
        return tile
    s = min(icon / im.width, icon / im.height, 1.0)  # never upscale
    w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
    im2 = im.resize((w, h), Image.Resampling.LANCZOS) if (w, h) != im.size else im
    tile.alpha_composite(im2, ((size - w) // 2, (size - h) // 2))
    return tile


def sheet(rows: list[tuple[str, Path, int]], size: int, bg, out: Path) -> None:
    """rows: (label, folder, icon_px). Columns = golden names."""
    label_w = 70
    header_h = 14
    W = label_w + size * len(names)
    H = header_h + size * len(rows)
    img = Image.new("RGBA", (W, H), bg)
    d = ImageDraw.Draw(img)
    tcol = (0, 0, 0, 255) if bg == LIGHT else (255, 255, 255, 255)
    for c, n in enumerate(names):
        d.text((label_w + c * size + 2, 2), n.replace(".png", ""), font=FONT, fill=tcol)
    for r, (label, folder, icon) in enumerate(rows):
        y = header_h + r * size
        d.text((2, y + size // 2 - 5), label, font=FONT, fill=tcol)
        for c, n in enumerate(names):
            img.alpha_composite(cell(load(folder, n), size, icon, bg), (label_w + c * size, y))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out)
    print("sheet", out.relative_to(REPO))


def zoom3x(out: Path, crop: int = 84) -> None:
    """3x nearest crops centered on the top of the opaque core: B1 vs aa_in."""
    z = crop * 3
    label_w = 70
    header_h = 14
    W = label_w + z * len(names)
    H = header_h + z * 2
    img = Image.new("RGBA", (W, H), LIGHT)
    d = ImageDraw.Draw(img)
    for c, n in enumerate(names):
        d.text((label_w + c * z + 2, 2), n.replace(".png", ""), font=FONT, fill=(0, 0, 0, 255))
    d.text((2, header_h + z // 2), "B1 live", font=FONT, fill=(0, 0, 0, 255))
    d.text((2, header_h + z + z // 2), "aa_in", font=FONT, fill=(0, 0, 0, 255))
    for c, n in enumerate(names):
        base = load(LIVE, n)
        a = np.array(base.getchannel("A"))
        ys, xs = np.where(a >= 250)
        if len(xs):
            cx = int(xs.mean())
            cy = int(ys.min()) + crop // 4  # top of the opaque core: ears/head joins
        else:
            cx = cy = 128
        x0 = max(0, min(256 - crop, cx - crop // 2))
        y0 = max(0, min(256 - crop, cy - crop // 4))
        for r, folder in enumerate((LIVE, AAIN)):
            im = load(folder, n)
            tile = Image.new("RGBA", (crop, crop), LIGHT)
            tile.alpha_composite(im.crop((x0, y0, x0 + crop, y0 + crop)))
            img.alpha_composite(
                tile.resize((z, z), Image.Resampling.NEAREST), (label_w + c * z, header_h + r * z)
            )
    img.convert("RGB").save(out)
    print("sheet", out.relative_to(REPO))


def _hue_on_mask(arr: np.ndarray, mask: np.ndarray) -> float:
    px = arr[mask]
    if len(px) == 0:
        return -1.0
    rgb = px[:, :3]
    asub = px[:, 3:4] / 255.0
    straight = np.clip(rgb / np.maximum(asub, 1e-3), 0, 255) / 255.0
    hues = []
    for p in straight[:: max(1, len(straight) // 2000)]:
        h, s, v = colorsys.rgb_to_hsv(*p)
        if s > 0.15 and v > 0.1:
            hues.append(h * 360.0)
    return float(np.median(hues)) if hues else -1.0


def mid_alpha_stats(name: str) -> tuple[int, int, float, float]:
    """INV-1 counts on each image's own mid-alpha mask; INV-3 hue on the SAME
    mask (live B1's mid-alpha pixels) for both images, so membership shifts at
    the join cannot fake a hue drift."""
    b1 = np.array(load(LIVE, name)).astype(np.float32)
    aa = np.array(load(AAIN, name)).astype(np.float32)
    mid_b1 = (b1[:, :, 3] > 20) & (b1[:, :, 3] < 200)
    mid_aa = (aa[:, :, 3] > 20) & (aa[:, :, 3] < 200)
    hue_b1 = _hue_on_mask(b1, mid_b1)
    hue_aa = _hue_on_mask(aa, mid_b1)
    return int(mid_b1.sum()), int(mid_aa.sum()), hue_b1, hue_aa


def opaque_extent(folder: Path, name: str) -> tuple[int, int]:
    im = load(folder, name)
    a = np.array(im.getchannel("A"))
    ys, xs = np.where(a >= 250)
    if len(xs) == 0:
        return 0, 0
    return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def main() -> int:
    rows_map = [("TiMXL", TIMXL, 48), ("B1 live", LIVE, 48), ("aa_in", AAIN, 48)]
    sheet(rows_map, 56, LIGHT, SHEETS / "fable_mapsize_light.png")
    sheet(rows_map, 56, DARK, SHEETS / "fable_mapsize_dark.png")
    rows_256 = [("TiMXL", TIMXL, 256), ("B1 live", LIVE, 256), ("aa_in", AAIN, 256)]
    sheet(rows_256, 260, LIGHT, SHEETS / "fable_canvas256_light.png")
    sheet(rows_256, 260, DARK, SHEETS / "fable_canvas256_dark.png")
    zoom3x(SHEETS / "fable_zoom3x_inner.png")

    print()
    print(f"{'file':16s} {'mid b1':>7s} {'mid aa':>7s} {'INV1':>6s} {'hue b1':>7s} {'hue aa':>7s} {'dhue':>5s}")
    fail = False
    for n in names:
        cb, ca, hb, ha = mid_alpha_stats(n)
        ratio = ca / cb if cb else float("nan")
        dh = abs(ha - hb) if (ha >= 0 and hb >= 0) else 0.0
        dh = min(dh, 360 - dh)
        flag = ""
        if cb and ratio < 0.60:
            flag += " INV1-FAIL"
            fail = True
        if dh > 10.0:
            flag += " INV3-FAIL"
            fail = True
        print(f"{n:16s} {cb:7d} {ca:7d} {ratio:6.2f} {hb:7.1f} {ha:7.1f} {dh:5.1f}{flag}")
    print()
    for n in ("25_a1.png", "83_a1.png"):
        wb, hb2 = opaque_extent(LIVE, n)
        wa, ha2 = opaque_extent(AAIN, n)
        print(f"_a1 opaque extent {n}: B1 {wb}x{hb2}  aa_in {wa}x{ha2}")
    if fail:
        print("INVARIANT FAILURES PRESENT")
        return 1
    print("invariants: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
