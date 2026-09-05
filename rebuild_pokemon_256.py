#!/usr/bin/env python3
"""Rebuild bigfun-outline-uicons/pokemon to 256×256 with locked sample pipeline.

Locked (Kelly-approved 2026-09-04):
  - Prefer PokeMiners Pokemon - 256x256 (via enhance_all.resolve_pokemon)
  - Canvas 256×256
  - Outer ~5px solid black stroke, soft OUTER AA only (ring outside silhouette)
  - Body alpha B1: harden within CUT_PX of opaque core; keep source mid-alpha beyond
  - Stroke-safe empty pad ≥5px (smoke may hit edge)
  - Shadow _a1: light purple wash + shadow_icon on top last @ ~1.12×
  - Purified _a2: same body pipeline (no smoke); keep existing if no source
  - scrub_white_only after composite (keep writer)
"""
from __future__ import annotations

import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT_DIR = Path(os.environ.get("BIGFUN_OUT", ROOT / "pokemon"))


def _find_pogo_assets() -> Path:
    env = os.environ.get("POGO_ASSETS", "").strip()
    if env:
        return Path(env)
    for cand in (ROOT.parent / "pogo_assets", Path("/workspace/pogo_assets")):
        if cand.exists():
            return cand
    return Path("/workspace/pogo_assets")


def _find_enhance_dir() -> Path:
    env = os.environ.get("BIGFUN_ENHANCE_DIR", "").strip()
    cands = []
    if env:
        cands.append(Path(env))
    cands.extend(
        [
            ROOT / "scripts",
            ROOT.parent / "wwm-uicons",
            Path("/workspace/wwm-uicons"),
        ]
    )
    for cand in cands:
        if (cand / "enhance_all.py").exists():
            return cand
    raise SystemExit(
        "enhance_all.py with resolve_pokemon was not found. "
        "Copy the workspace module to scripts/enhance_all.py or set BIGFUN_ENHANCE_DIR. "
        "Do not use kbtbc/wwm-outline-uicons/scripts/enhance_all.py (no resolver)."
    )


POGO_ASSETS = _find_pogo_assets()
ICON = POGO_ASSETS / "Images" / "Rocket" / "shadow_icon.png"
load_indexes = None
resolve_pokemon = None
enhance_rgba = None


def _ensure_enhance() -> None:
    global load_indexes, resolve_pokemon, enhance_rgba
    if resolve_pokemon is not None:
        return
    sys.path.insert(0, str(_find_enhance_dir()))
    from enhance_all import load_indexes as li, resolve_pokemon as rp, enhance_rgba as er

    load_indexes, resolve_pokemon, enhance_rgba = li, rp, er

CANVAS = 256
STROKE_PX = 5.0
AA_OUT = 1.35
CUT_PX = 1.0  # B1: harden body AA within this distance of opaque core
SIL_THR = 20
SOLID_THR = 128
STROKE_SAFE = 5
SMOKE_SCALE = 1.12
UICONS_POKE = re.compile(
    r"^(\d+)(?:_b(\d+))?(?:_e(\d+))?(?:_f(\d+))?(?:_c(\d+))?(?:_g(\d+))?(?:_a(\d+))?(_s)?\.png$"
)


def premultiply(im: Image.Image) -> Image.Image:
    a = np.array(im.convert("RGBA"), dtype=np.float32)
    a[:, :, :3] *= a[:, :, 3:4] / 255.0
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def edt_outside(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    INF = 10**9
    g = np.where(mask, 0, INF).astype(np.int64)
    for x in range(w):
        for y in range(1, h):
            g[y, x] = min(g[y, x], g[y - 1, x] + 1)
        for y in range(h - 2, -1, -1):
            g[y, x] = min(g[y, x], g[y + 1, x] + 1)
    dist2 = np.empty((h, w), dtype=np.float64)
    for y in range(h):
        f = g[y].astype(np.float64)
        f2 = f * f
        k = 0
        vidx = np.zeros(w, dtype=np.int32)
        z = np.zeros(w + 1, dtype=np.float64)
        vidx[0] = 0
        z[0] = -np.inf
        z[1] = np.inf
        for q in range(1, w):
            s = ((f2[q] + q * q) - (f2[vidx[k]] + vidx[k] * vidx[k])) / (
                2 * q - 2 * vidx[k] + 1e-12
            )
            while s <= z[k]:
                k -= 1
                s = ((f2[q] + q * q) - (f2[vidx[k]] + vidx[k] * vidx[k])) / (
                    2 * q - 2 * vidx[k] + 1e-12
                )
            k += 1
            vidx[k] = q
            z[k] = s
            z[k + 1] = np.inf
        k = 0
        for q in range(w):
            while z[k + 1] < q:
                k += 1
            dist2[y, q] = (q - vidx[k]) ** 2 + f2[vidx[k]]
    return np.sqrt(dist2)


def scrub_white_only(a: np.ndarray) -> np.ndarray:
    rgb = a[:, :, :3].astype(np.float32)
    al = a[:, :, 3].astype(np.float32)
    mn = rgb.min(2)
    mx = rgb.max(2)
    lum = rgb.mean(2)
    from numpy import roll

    is_black = (al > 200) & (lum < 45)
    near_black = (
        is_black
        | roll(is_black, 1, 0)
        | roll(is_black, -1, 0)
        | roll(is_black, 1, 1)
        | roll(is_black, -1, 1)
    )
    whiteish = (mn > 140) & (al > 60) & ((mx - mn) < 80)
    fringe = near_black & whiteish
    a[fringe, 0] = 0
    a[fringe, 1] = 0
    a[fringe, 2] = 0
    a[fringe, 3] = np.maximum(a[fringe, 3], 220)
    return a


def add_outer_stroke(
    im: Image.Image,
    stroke_px: float = STROKE_PX,
    aa_out: float = AA_OUT,
    cut_px: float = CUT_PX,
) -> Image.Image:
    """Outer-ring stroke + B1 body alpha (Kelly-locked 2026-09-04, CUT_PX=1.0).

    Stroke is only outside the silhouette (plus a tiny underlap under the opaque
    core). Filling black under the whole silhouette blacks out translucent wings.

    B1 body alpha: opaque within CUT_PX of the opaque core (alpha >= SOLID_THR);
    beyond that, keep source mid-alpha so wings survive. Soft OUTER AA only.
    scrub_white_only after composite.
    """
    im = premultiply(im)
    arr = np.array(im.convert("RGBA")).astype(np.float32)
    alpha = arr[:, :, 3]
    sil = alpha > SIL_THR
    solid = alpha >= SOLID_THR

    dist_out = edt_outside(sil)
    hard = stroke_px
    soft = stroke_px + aa_out
    stroke_a = np.zeros_like(alpha, dtype=np.float32)
    # Outer ring only — do not fill under silhouette
    stroke_a[(~sil) & (dist_out <= hard)] = 255.0
    band = (~sil) & (dist_out > hard) & (dist_out <= soft)
    stroke_a[band] = 255.0 * (1.0 - (dist_out[band] - hard) / max(soft - hard, 1e-6))
    # Tiny underlap under opaque core so the ring seats against hard body edge
    dist_in_solid = edt_outside(~solid)
    under = solid & (dist_in_solid <= 0.6)
    stroke_a[under] = np.maximum(stroke_a[under], 255.0)

    sa = Image.fromarray(np.clip(stroke_a, 0, 255).astype(np.uint8), "L").filter(
        ImageFilter.GaussianBlur(0.45)
    )
    stroke_rgba = np.zeros((*alpha.shape, 4), dtype=np.float32)
    stroke_rgba[:, :, 3] = np.array(sa).astype(np.float32)
    stroke_im = Image.fromarray(np.clip(stroke_rgba, 0, 255).astype(np.uint8), "RGBA")

    # Scrub soft stroke AA on the stroke layer ONLY — never on body/wings.
    sa_arr = np.array(stroke_im.convert("RGBA"))
    s_rgb = sa_arr[:, :, :3].astype(np.float32)
    s_al = sa_arr[:, :, 3].astype(np.float32)
    s_lum = s_rgb.mean(2)
    s_chroma = s_rgb.max(2) - s_rgb.min(2)
    soft_stroke = (s_al > 5) & (s_al < 250) & (s_lum < 85) & (s_chroma < 40)
    sa_arr[soft_stroke, 0] = 0
    sa_arr[soft_stroke, 1] = 0
    sa_arr[soft_stroke, 2] = 0
    hard_stroke = s_al >= 250
    sa_arr[hard_stroke, 0] = 0
    sa_arr[hard_stroke, 1] = 0
    sa_arr[hard_stroke, 2] = 0
    stroke_im = Image.fromarray(sa_arr, "RGBA")

    sa_safe = np.maximum(alpha, 1e-6)[..., None]
    straight = np.clip(arr[:, :, :3] / (sa_safe / 255.0), 0, 255)

    dist_to_core = edt_outside(solid).astype(np.float32)
    dist_to_core = np.where(solid, 0.0, dist_to_core)
    near_core = dist_to_core <= cut_px
    body_a = np.zeros_like(alpha, dtype=np.float32)
    harden = near_core & (alpha > SIL_THR)
    body_a[harden] = 255.0
    far = (~near_core) & (alpha > SIL_THR)
    body_a[far] = alpha[far]

    body_out = np.zeros_like(arr)
    body_out[:, :, :3] = straight
    body_out[:, :, 3] = body_a
    body_out[body_a < 1, :3] = 0
    body_im = Image.fromarray(np.clip(body_out, 0, 255).astype(np.uint8), "RGBA")

    outlined = Image.alpha_composite(stroke_im, body_im)
    a = scrub_white_only(np.array(outlined.convert("RGBA")))
    return premultiply(Image.fromarray(a, "RGBA"))


def body_wash(sprite: Image.Image, strength: float = 0.22) -> Image.Image:
    arr = np.array(sprite).astype(np.float32)
    a = arr[:, :, 3:4] / 255.0
    purple = np.array([95, 30, 160], dtype=np.float32)
    xs = np.linspace(0, 1, arr.shape[1])[None, :, None]
    local = strength * (0.55 + 0.45 * xs)
    arr[:, :, :3] = arr[:, :, :3] * (1 - local) + purple * local
    arr[:, :, :3] *= a
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def ensure_stroke_safe(im: Image.Image, pad: int = STROKE_SAFE) -> Image.Image:
    im = im.convert("RGBA")
    w, h = im.size
    alpha = np.array(im.getchannel("A"))
    ys, xs = np.where(alpha > 20)
    if len(xs) == 0:
        return im
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    if min(x0, y0, w - x1, h - y1) >= pad:
        return im
    cw, ch = x1 - x0, y1 - y0
    s = min((w - 2 * pad) / max(cw, 1), (h - 2 * pad) / max(ch, 1))
    content = im.crop((x0, y0, x1, y1)).resize(
        (max(1, int(round(cw * s))), max(1, int(round(ch * s)))), Image.Resampling.LANCZOS
    )
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(content, ((w - content.width) // 2, (h - content.height) // 2), content)
    return premultiply(out)


_SMOKE_ICON = None


def shadow_on_top(base: Image.Image, scale: float = SMOKE_SCALE, opacity: float = 0.95) -> Image.Image:
    global _SMOKE_ICON
    if _SMOKE_ICON is None:
        _SMOKE_ICON = Image.open(ICON).convert("RGBA")
    icon = _SMOKE_ICON
    tw = int(base.width * scale)
    th = int(icon.height * tw / max(icon.width, 1))
    icon = icon.resize((tw, th), Image.Resampling.LANCZOS)
    r, g, b, a = icon.split()
    rgb = ImageEnhance.Color(Image.merge("RGB", (r, g, b))).enhance(1.15)
    icon = Image.merge("RGBA", (*rgb.split(), a))
    ia = np.array(icon)
    ia[:, :, 3] = (ia[:, :, 3].astype(np.float32) * opacity).clip(0, 255).astype(np.uint8)
    icon = Image.fromarray(ia, "RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ox = (base.width - icon.width) // 2 + int(base.width * 0.04)
    oy = (base.height - icon.height) // 2 - int(base.height * 0.01)
    layer.paste(icon, (ox, oy), icon)
    return Image.alpha_composite(base, layer)


def process(raw: Image.Image, aura: int | None) -> Image.Image:
    """aura: 1=shadow, 2=purified, None=normal."""
    work = CANVAS + int(STROKE_PX + AA_OUT) * 2 + STROKE_SAFE * 2 + 8
    im = raw.convert("RGBA")
    # Ignore near-zero alpha fringe — PokeMiners 256 often has 1-alpha edge pixels
    # that make getbbox() return almost the full canvas and leave the sprite tiny.
    alpha = im.getchannel("A")
    mask = alpha.point(lambda a: 255 if a > 20 else 0)
    bb = mask.getbbox()
    if bb:
        im = im.crop(bb)
    target = CANVAS - 2 * (int(STROKE_PX + AA_OUT) + STROKE_SAFE)
    s = min(target / max(im.width, 1), target / max(im.height, 1))
    nw = max(1, int(round(im.width * s)))
    nh = max(1, int(round(im.height * s)))
    small = im.resize((nw, nh), Image.Resampling.LANCZOS)
    big = Image.new("RGBA", (work, work), (0, 0, 0, 0))
    big.paste(small, ((work - nw) // 2, (work - nh) // 2), small)
    if aura == 1:
        big = body_wash(big, 0.22)
    big = enhance_rgba(big)
    big = add_outer_stroke(big)
    off = (work - CANVAS) // 2
    body = big.crop((off, off, off + CANVAS, off + CANVAS))
    body = ensure_stroke_safe(body, STROKE_SAFE)
    if aura == 1:
        return shadow_on_top(body)
    return body


def parse_aura(name: str) -> int | None:
    m = UICONS_POKE.match(name)
    if not m:
        return None
    a = m.group(7)
    return int(a) if a else None


def resolve_base_name(name: str) -> str:
    """Strip _a1/_a2 for source resolve — body art is shared."""
    return re.sub(r"_a[12](?=_s)?", "", name).replace("_a1", "").replace("_a2", "")


_WORKER_READY = False

def worker(name: str) -> tuple[str, str]:
    global _WORKER_READY
    try:
        _ensure_enhance()
        if not _WORKER_READY:
            load_indexes()
            _WORKER_READY = True
        aura = parse_aura(name)
        # resolve without aura so we get base sprite
        key = name
        if aura:
            key = re.sub(r"_a" + str(aura), "", name)
        src, tag = resolve_pokemon(key)
        if src is None:
            return name, "skip:no-source"
        out = process(Image.open(src), aura=aura if aura in (1, 2) else None)
        out.save(OUT_DIR / name, optimize=True)
        return name, f"ok:{tag}:a{aura}"
    except Exception as e:
        return name, f"err:{e}"


def main():
    _ensure_enhance()
    load_indexes()
    names = sorted(p.name for p in OUT_DIR.glob("*.png"))
    if len(sys.argv) > 1:
        prefixes = []
        for arg in sys.argv[1:]:
            prefixes.extend(x.strip() for x in arg.split(",") if x.strip())
        keep = []
        for n in names:
            dex = n.split("_", 1)[0].replace(".png", "")
            if dex in prefixes:
                keep.append(n)
        names = keep
        print(f"filter dex {prefixes} → {len(names)} files", flush=True)
    print(f"rebuilding {len(names)} pokemon icons → 256 pipeline", flush=True)
    t0 = time.time()
    ok = skip = err = 0
    # ProcessPool needs picklable worker — run sequential chunks with threads instead
    # EDT is python-heavy; use processes via top-level worker
    with ProcessPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(worker, n) for n in names]
        for i, fut in enumerate(as_completed(futs), 1):
            name, status = fut.result()
            if status.startswith("ok"):
                ok += 1
            elif status.startswith("skip"):
                skip += 1
            else:
                err += 1
                print(name, status, flush=True)
            if i % 500 == 0 or i == len(names):
                print(f"  {i}/{len(names)} ok={ok} skip={skip} err={err} {time.time()-t0:.0f}s", flush=True)
    print(f"done ok={ok} skip={skip} err={err} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
