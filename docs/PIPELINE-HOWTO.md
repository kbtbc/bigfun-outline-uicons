# bigfun-outline-uicons — Pipeline How-To Guide

**Repo:** https://github.com/kbtbc/bigfun-outline-uicons  
**Raw base:** `https://raw.githubusercontent.com/kbtbc/bigfun-outline-uicons/main/`  
**Owner:** Kelly Britt (`kbtbc`) / BigFun  
**Scope:** Pokémon GO map icons only (UIcons-compatible). Home-only / unreleased species are out of scope.  
**Document date:** 2026-09-04  

This is the single reference for building the Pokémon icon pack: what is in force, what
is broken, and how to change it. **Start at §0** — it carries the whole picture in one
page. §§1–12 are the detail behind it, and §7 is the record of *why* each decision was
made, not something you need to read first.

---

## 0. Current state — start here

### 0.1 Status at a glance

| Area | State |
|---|---|
| Source resolution: forms, costumes, Unown, Burmy, Darmanitan, Genesect, Squawkabilly | **Working** — §5, §8 |
| Filename grammar: shiny / gender / evo / bread / alignment flags | **Working** — §4 |
| 256 canvas, contain-fit, stroke-safe pad | **Working** — §6.2, §6.5 |
| Outer stroke: rounded EDT expansion, soft outer AA | **Working** — §6.4 |
| Body/stroke join, no white fringe | **Working, verified by measurement** — §6.7, §7.12 |
| Shadow `_a1` purple wash + smoke | **Working** — §6.8 |
| Translucent wings (Yanma, Yanmega, Combee, Beedrill) | **Method correct, pack broken** — §0.3 |
| Inner jaggies (`aa_in` coverage ramp) | **Prototype; currently introduces a white line** — §6.12 |
| Reproducibility (build script in version control) | **Missing** — §2, §14.1 |
| Automated regression checks | **None** — §14.2 |

### 0.2 Every issue encountered, and the solution in force

| # | Issue | Solution in force | Where | In the pack? |
|---|---|---|---|---|
| 1 | Icons upscaled from 93×93 looked soft | Always source PokeMiners `Pokemon - 256x256`; never upscale when a 256 original exists | §1, §5 | Yes |
| 2 | Form / costume variants resolved to wrong or low-res art | Resolve by **game-master proto first** (`UNOWN_A`, `DARMANITAN_ZEN`), then aliases; else 256 Addressable `pm{dex}.f{PROTO}.icon.png` | §5, §8 | Yes |
| 3 | `getbbox()` counted a 1-alpha halo → tiny sprites, thick-looking borders | Crop on `alpha > 20`, never raw alpha | §6.2 | Yes |
| 4 | Square `MaxFilter` dilate gave blocky outline tips | Rounded expansion via Euclidean distance transform | §6.4 | Yes |
| 5 | Harsh cut-out edge against light UI | Soft **outer** AA: distance fade across `AA_OUT`, plus a light blur | §6.4, §6.7 | Yes |
| 6 | Soft AA on **both** sides produced a white inner hairline | Soft outer only; body hard-cut opaque at `A >= 128`; `scrub_white_only` for stragglers | §6.6, §6.7, §7.6 | Yes — **measured clean**, §7.12 |
| 7 | Ear / wing tips looked clipped | `STROKE_SAFE >= 5` empty pad via `ensure_stroke_safe`; QA sheets must show the full 256 canvas | §6.5, §6.10 | Yes |
| 8 | Shadow `_a1` shipped without smoke, or with borrowed art | Build our own: purple wash → stroke pipeline → `shadow_icon` on top at ~1.12×. Never copy wwm's baked `_a1` | §6.8 | Yes |
| 9 | Iterating on one species regressed others | Lock one pipeline; prove it on a **mixed** sheet before any full rebuild | §7.4, §6.10 | Process rule |
| 10 | Translucent wings deleted; sprite left at ~44% canvas | Silhouette `alpha > 20`; keep mid-alpha colour; outer **ring** only — never fill black under the whole mask | §6.4, §7.10 | **No** — §0.3 |
| 11 | Inner stroke edge stair-steps at 3× zoom | Coverage ramp `aa_in ≈ 1.25` blending into black | §6.7, §7.11 | **No** — prototype |
| 12 | White line inside the border on the `aa_in` prototype | Back the ramp with a signed-DF fill, so black is solid *under* the body edge | §6.12 | **No** — specified, not built |
| 13 | Restoring wings by gating black on source alpha blacks them out | Gate geometrically on distance, never on `A` — core AA and wing pixels share the same alpha | §6.12, §7.13 | **No** — constraint, not yet implemented |

Rows 1–9 are the accumulated working pipeline: they are why forms, costumes, alignments
and the 256 canvas all behave consistently across ~18k icons. Rows 10–13 are open.

### 0.3 Broken right now (measured 2026-09-04, see §7.12)

**1. Low-fill / wing-chop in the shipped pack (92 icons, 11 dex).**
`193`, `415`, `469` ship at fill 0.44–0.46 with **zero** mid-alpha pixels, against a spec
of 0.93–0.96. Contain-fit sizes the sprite on `alpha > 20` (wings included), then the
`alpha >= 128` body cut deletes them — predicted and measured agree within 0.03.
**The method in §6.4 is correct; the pack does not have it.** Full sweep also hits
`15`, `742`, `743`, `751`, `938` (same source-art defect class; forms follow the body)
plus `577` / `578` / `738` (separate cause — §14.3). `742`/`743` are **not** capped by
tiny Addressable size — contain-fit upscales; their fill matches the wing-cut model.

**2. The `aa_in` prototype introduces a white inner line.** §6.12 has the cause and fix.
This is *not* a defect in the shipped pack — §7.12 measures the live join as clean.

**3. `rebuild_pokemon_256.py` is in no repository.** §2. No rebuild is reproducible,
reviewable, or revertible.

**4. There are no automated checks.** §14.2. Issue 10 is documented in this guide, was
solved in the script, and still shipped broken. Prose cannot fail a build.

### 0.4 Next actions, in order

1. **Commit `rebuild_pokemon_256.py`.** Nothing else is verifiable until the build script
   is under version control. §14.1
2. **Add INV-1 and INV-3** — wing pixels preserved, translucent hue preserved — and run
   them over a golden set. These are the two checks that would have caught §7.10 and
   §7.13 without depending on anyone's eye. §14.2
3. **Fix the wing chop in the pack.** The method is already §6.4; confirm the script
   matches it, rebuild the affected dexes, verify with INV-1.
4. **Explain `577` Solosis and `738` Vikavolt.** The sweep is complete and eight of the
   ten dex are confirmed against source; these two are not accounted for by the body cut
   and need a separate cause. §14.3
5. **Only then** take up the `aa_in` ramp with the §6.12 backing fill, prototyped on
   `25` / `649` / `931` for the line and `193` / `469` / `415` for the wings.

Steps 1–2 come before step 3, and step 3 before step 5. The ordering is the point:
§7.12 showed the pack can ship a documented, already-solved defect with nobody noticing.

---

### 0.5 Update — B1 wing-cut shipped (2026-09-04 evening)

This subsection **adds** status after §0.1–0.4. Earlier rows above are kept as the
audit trail from earlier the same day.

| Area | State after `42cc026` |
|---|---|
| Body alpha | **B1 locked** — harden within `CUT_PX = 1.0` of opaque core (`alpha >= 128`); keep source mid-alpha beyond. Kelly approved. |
| Outer stroke | **Outer ring only** (plus tiny underlap under opaque core). Do not fill black under the whole silhouette. |
| Translucent wings | **Fixed in pack** for the wing-cut class (`15`, `193`, `415`, `469`, `742`, `743`, `751`, `938` and formes). Full Pokémon rebuild applied. |
| `577` / `738` undersize | **Fixed by rebuild** — fill returned to ~0.93–0.96 (older build artifacts, not live `ensure_stroke_safe`). |
| `rebuild_pokemon_256.py` | **On GitHub `main`** in `42cc026`. |
| Full Pokémon rebuild | **18,156 ok**, 5 skip (`0.png` placeholders), 0 err. Pushed with the script. |
| `aa_in` inner coverage | Still **prototype only**. Not in this push. |
| Build-time invariants | Still **none** (§14.2). Still the next reliability gap. |
| Weekly PokeMiners sync | **Requested** — script/routine not finished yet. See §14.7. |

**CUT_PX sweep (production recommendation Kelly locked):** tested 0.5 / 1.0 / 1.5 / 2.0 on
controls + wing class. `0.5` restored the most wing mid-alpha but soft-fringed opaque
bodies (Pikachu / Darmanitan mid ratios above live). `1.0` kept strong wing restore and
matched opaque-control mid ratios. `1.5` / `2.0` added little wing keep.

**Honest compare note vs TiMXL73:** at display size, upscaling TiMXL's 93×93 to 256 makes
TiMXL look soft. Fairer check is both at ~map size (~93) and native side by side. Our
wins that hold either way: PokeMiners 256 source, square canvas, real `shadow_icon` smoke,
B1 wing keep, thicker intentional outline. Tradeoffs: heavier stroke and saturation punch
can read as "sticker" / over-processed next to TiMXL's lighter outline; `aa_in` jaggies
and some dark source wings (Yanma) remain.

---

## 1. Goal

Produce a **high-quality, consistent** UIcons Pokémon pack for Pokémon GO maps:

| Requirement | Rule |
|---|---|
| Source art | **PokeMiners `Pokemon - 256x256` first.** Addressable only when no native 256 match. |
| Never | Upscale old 93×93 / wwm / TiMXL icons when a PokeMiners 256 original exists. |
| Never | Guess form/costume mappings, borrow inferior art, or invent substitutes. |
| Canvas | **256×256** square, contain-fit. |
| Stroke | Outer **~5px** solid black, soft **outer** AA, no inner white fringe. |
| Padding | **pad ≥ 5** on all sides for the stroke; smoke may hit the edge. |
| Shadow `_a1` | Our composite: purple body wash + `shadow_icon` on top last (~1.12×). Do **not** copy wwm baked `_a1`. |
| Filenames | UIcons convention only (`pokemon/25.png`, `201_f1.png`, `555_f139.png`). |
| Validation | Samples must show the **full uncropped 256 canvas**; check against GO / TiMXL before locking. |

Quality and consistency beat speed. Lock a **whole-set** pipeline on a mixed sample sheet before any full rebuild.

---

## 2. Repositories and paths

| Role | Location |
|---|---|
| Output pack | https://github.com/kbtbc/bigfun-outline-uicons |
| Rebuild script | `rebuild_pokemon_256.py` (repo root; also `/workspace/rebuild_pokemon_256.py`) |
| Source resolver / enhance | `/workspace/wwm-uicons/enhance_all.py` (`resolve_pokemon`, `enhance_rgba`) |
| PokeMiners assets | `/workspace/pogo_assets` ← clone of [PokeMiners/pogo_assets](https://github.com/PokeMiners/pogo_assets) |
| Native 256 folder | `pogo_assets/Images/Pokemon - 256x256/` |
| Addressable (often smaller art on 256 canvas) | `…/Pokemon - 256x256/Addressable Assets/` |
| Low-res Addressable | `pogo_assets/Images/Pokemon/Addressable Assets/` (do not prefer) |
| Shadow texture | `pogo_assets/Images/Rocket/shadow_icon.png` |
| Game master / forms | `/workspace/master-latest.json` (dex forms, protos) |
| Sample / compare sheets | `/workspace/uicon-samples/fx-v2/quality256/` |
| Diagnostic tool | `icondiag.py` — radial-profile halo audit, geometry metrics, magenta sheet |

> **Correction (verified 2026-09-04).** `rebuild_pokemon_256.py` is **not on GitHub
> `main`** (no `.py` files published). It exists in the workspace and may be present in
> a local checkout as an unpushed file — still **not recoverable from origin**. Until it
> is committed and pushed, no rebuild is reproducible from the repo alone.
>
> `enhance_all.py` *is* public, at `kbtbc/wwm-outline-uicons/scripts/enhance_all.py`
> (3,595 bytes) — note this differs from the `/workspace/wwm-uicons/` path in the table
> above.
>
> Committing `rebuild_pokemon_256.py` costs nothing and is the highest-value change
> available to this project.

> **Update (2026-09-04 evening).** `rebuild_pokemon_256.py` **is on GitHub `main`** as of
> commit `42cc026`, with the full B1 Pokémon rebuild. The correction above remains as the
> earlier same-day finding. Prefer the repo root copy; `/workspace/rebuild_pokemon_256.py`
> is the working mirror.

| Earlier outline pack | https://github.com/kbtbc/wwm-outline-uicons (2–3px inset era) |
| Upstream layout reference | https://github.com/WatWowMap/wwm-uicons |
| Spec / naming | https://github.com/UIcons/UIcons |

---

## 3. Locked pipeline parameters (as of 2026-09-04)

These are the production constants in `rebuild_pokemon_256.py`:

```text
CANVAS       = 256
STROKE_PX    = 5.0
AA_OUT       = 1.35          # soft fade outside the hard stroke ring
STROKE_SAFE  = 5             # minimum empty pad after stroke
SMOKE_SCALE  = 1.12          # shadow_icon vs canvas
Crop alpha   > 20            # ignore 1-alpha fringe when measuring bbox
Silhouette   alpha > 20      # includes translucent wings
Solid body   alpha ≥ 128     # hard-cut opaque core (current live)
```

**Addendum (B1, Kelly-locked 2026-09-04, shipped in `42cc026`):**

```text
CUT_PX       = 1.0           # B1: harden body AA within this distance of opaque core
SIL_THR      = 20            # silhouette / mid-alpha keep threshold
SOLID_THR    = 128           # opaque core for B1 distance cut (same threshold as above)
```

Body alpha is no longer "clear everything below 128." Soft outer AA only remains.
Stroke is an outer ring only. The `Solid body` line above still names the opaque-core
threshold; B1 uses it as the distance origin, not as a hard wipe of mid-alpha wings.

**Pending (prototyped, not yet full-pack applied):** soft **inner** AA via body coverage ramp over black stroke (`aa_in ≈ 1.25`) to kill inner jaggies without a white fringe. See §7.10, and §6.12 for why the prototype currently produces a white fringe and how to back it out.

---

## 4. UIcons filename grammar

Pokémon files match:

```text
{dex}[_b{bread}][_e{evo}][_f{form}][_c{costume}][_g{gender}][_a{alignment}][_s].png
```

Examples:

| File | Meaning |
|---|---|
| `25.png` | Pikachu default |
| `25_a1.png` | Shadow |
| `25_a2.png` | Purified |
| `25_s.png` | Shiny |
| `6_e1.png` / `6_e2.png` | Mega X / Mega Y style evo |
| `555_f139.png` | Darmanitan Zen (form id 139) |
| `201_f1.png` | Unown A |
| `412_f119.png` | Burmy Sandy |
| `415_g2.png` | Combee female |

Alignment `_a1` / `_a2` shares body art with the base name; aura is applied in `process()`.

---

## 5. Source resolution order

Implemented in `enhance_all.resolve_pokemon`:

1. Parse UIcons name → dex, form, costume, evo, gender, shiny, alignment.
2. Build form tokens from game master **full proto first** (`UNOWN_A`, `BURMY_PLANT`, `DARMANITAN_ZEN`, …), then aliases.
3. Prefer **numbered** `Pokemon - 256x256` files:  
   `pokemon_icon_{ddd}_{form}_{costume}[_shiny].png`
4. Else **256 Addressable**: `pm{dex}.f{PROTO}.icon.png` (and `.s` for shiny) under `Pokemon - 256x256/Addressable Assets/`.
5. Else low-res Addressable / other fallbacks only if nothing else exists.
6. **Never** upscale a 93×93 pack icon when a 256 source exists.

Tags returned: `"256"`, `"256-addr"`, `"addr"`, or miss.

---

## 6. Technical image-manipulation methods

Stack: **Python 3 + Pillow (PIL) + NumPy**. Parallel rebuild via `ProcessPoolExecutor` (4 workers). EDT for strokes is pure NumPy (no SciPy dependency).

### 6.1 Premultiplied alpha

```text
RGB_premul = RGB_straight × (A / 255)
```

Used before distance-field stroke so soft edges composite cleanly. After building body RGB, values are un-premultiplied (`RGB / (A/255)`) for straight-alpha compositing, then optionally premultiplied again on save path.

### 6.2 Content crop (ignore 1-alpha fringe)

PokeMiners 256 sprites often have a near-invisible **1-alpha** halo that makes `Image.getbbox()` return almost the full 256×256 frame. That left small species (e.g. Inkay `686`) tiny with a huge empty border and a visually “super-thick” stroke.

**Method:**

```text
mask = (alpha > 20) → binary
bbox = mask.getbbox()
crop to bbox
```

Then contain-fit into a working canvas sized for stroke + pad:

```text
work = CANVAS + 2*(STROKE_PX + AA_OUT) + 2*STROKE_SAFE + 8
target = CANVAS - 2*(STROKE_PX + AA_OUT + STROKE_SAFE)
scale = min(target/w, target/h)     # contain-fit, aspect preserved
LANCZOS resize → center-paste on transparent work canvas
```

### 6.3 Saturation / clarity punch

`enhance_rgba` (from `enhance_all`) runs before stroke — mild color/clarity enhancement on the RGBA sprite so GO art stays punchy after outlining.

### 6.4 Outer stroke via Euclidean distance transform (EDT)

**Not** a square `MaxFilter` dilate (that made blocky tips). **Rounded** silhouette expansion:

1. Build binary mask from alpha (`alpha > 20` so translucent wings count).
2. Compute **distance outside** the mask (`edt_outside`) — Felzenszwalb/Huttenlocher-style 2-pass EDT in NumPy.
3. Hard stroke ring: `0 < dist ≤ STROKE_PX` → alpha 255 (black).
4. Soft outer band: `STROKE_PX < dist ≤ STROKE_PX+AA_OUT` → alpha fades `255 → 0`.
5. Light Gaussian blur (~0.45) on the stroke alpha for outer AA.
6. Force stroke RGB to pure black; scrub accidental light fringe (see §6.6).
7. Composite: **stroke underneath, body on top** (`Image.alpha_composite`).

**Opaque body hard-cut (current live):** pixels with `alpha ≥ 128` become fully opaque; below that (except wings handling) cleared. That kills a soft white inner halo but creates **inner stair-step jaggies** (visible on Genesect at 3×).

**Wing-aware body:** mid-alpha pixels (`20 < A < 128`) keep their alpha so Yanma / Yanmega / Combee wings are not deleted. Critical: do **not** fill opaque black stroke *under* the entire silhouette, or translucent wings composite to muddy black. Stroke should be an **outer ring** (plus tiny underlap under opaque core only).

### 6.5 Stroke-safe padding

After cropping the work canvas back to 256×256, `ensure_stroke_safe`:

```text
measure content bbox at alpha > 20
if min margin < STROKE_SAFE (5):
    scale content down and re-center so all sides ≥ 5px empty
```

Smoke overlay is allowed to violate this (may hit edge).

### 6.6 White-fringe scrub

Soft AA + LANCZOS can leave bright near-black-adjacent pixels that read as a **white hairline** between body and stroke (especially on dark map tiles).

`scrub_white_only`:

```text
detect near-black stroke neighborhood
AND whiteish low-chroma pixels
→ force those RGB to black, boost alpha
```

Also: only blacken soft **stroke** pixels (neutral, low luminance). Never blacken **colored** translucent wing mid-alpha.

### 6.7 Soft outer AA vs soft inner AA

| Edge | Desired | Method | Failure mode if wrong |
|---|---|---|---|
| Outer (stroke → transparent) | Soft | DF fade + slight blur | Harsh cutout on light UI |
| Inner (body → stroke) | Soft into **black** | Ramp **body coverage** over black stroke (`aa_in≈1.25`), cosine ease | Soft into transparent/light → **white fringe**; RGB→black on wings → blacked-out wings |

**Recommended inner AA (prototyped):** at the opaque silhouette edge, over `aa_in` pixels inward, set body alpha = `255 * smoothstep(dist_in / aa_in)` while stroke sits underneath. Blend is into black, not white. **Not yet applied to full pack** as of this writing.

### 6.8 Shadow (`_a1`) composite

1. Optional **body wash**: lerp RGB toward purple `(95, 30, 160)` with horizontal bias (stronger on the right), strength ~0.22, premultiplied.
2. Run same stroke pipeline.
3. **`shadow_icon` on top last:** scale to `SMOKE_SCALE * canvas` (~1.12×), slight color boost, opacity ~0.95, offset slightly right/up, `alpha_composite` over the outlined body.

Do not paste wwm’s baked `_a1` art.

### 6.9 Purified (`_a2`)

Same body pipeline as normal (no smoke). If no dedicated source, body matches the non-alignment icon.

### 6.10 Sample / QA method

- Always render **full 256×256** on dark and light backgrounds.  
- Cropped “tight” compare sheets **hid real pad** and made ear/wing tips look clipped when they were not.  
- Metrics: `fill = max(content_w, content_h) / 256`, `pad = min margins at alpha>20`. Target fill ~0.93–0.96, pad ≥ 5 (except `_a1` smoke may show pad 0).  
- 3× nearest-neighbor zooms expose inner jaggies (Genesect cannon/head).

### 6.11 Rebuild invocation

```bash
# full pack
python3 rebuild_pokemon_256.py

# dex filter (comma-separated)
python3 rebuild_pokemon_256.py 15,193,415,469,742,743
```

Writes into `pokemon/`, preserves UIcons filenames, uses `resolve_pokemon` for sources.

---

### 6.12 Inner white boundary: cause and fix (for the `aa_in` coverage path)

Applies to the §7.11 coverage-AA prototype, which is where the white line appears.
§7.12 measures the shipped pack and finds no white line there, so this is a fix for the
prototype — not a repair of what ships, and not a reason to rebuild.

#### Why the coverage ramp produces it

§6.4 builds the stroke at `0 < dist <= STROKE_PX` — strictly **outside** the silhouette
mask — then blurs the stroke alpha by ~0.45. That blur is symmetric, so it pulls the
ring's *inner* alpha down as well as its outer.

The live pack gets away with this because the body is **hard-cut opaque** at `A >= 128`.
Body alpha is 255 right up to the cut, the join is fully covered, and total alpha is 255.
§7.12's measured profile confirms it: `A = 1.00` from d = 3.5 inward.

The `aa_in` ramp removes exactly that protection. It lowers body alpha across the join —
that is its entire purpose — and the ring underneath does not rise to compensate, because
it was built to stop at the mask edge:

```text
body_A < 255   over   stroke_A < 255   =>   total alpha < 255
```

A partially transparent band one to two pixels wide, sitting between body and stroke.
Invisible on a dark tile; on a light tile the background shows through it and reads as a
**white hairline**. This is §7.6's failure arriving by a different route: §7.6 softened
both sides, `aa_in` softens one side over a ring that cannot back it.

**The ramp is not the bug.** Blending body coverage into black is correct. The bug is
that there is no black underneath it to blend into.

#### The fix: back the ramp with a signed-distance fill

Build the black from a **signed** distance field of the opaque core, so it is solid under
the body rather than merely beside it:

```text
d_core = edt(core) - edt(~core) - 0.5    # negative inside; 0 on the alpha=0.5 contour
back   = clamp(0.5 + (STROKE_EDGE - d_core) / AA_OUT, 0, 1)
```

Because `d_core` is negative inside the core, `back` evaluates to **1 across the entire
core interior**, not just in a ring beside it. The `aa_in` ramp then always has opaque
black beneath it, total alpha stays 255 across the join, and no background can show
through at any tile colour.

`STROKE_EDGE = STROKE_PX + AA_OUT/2 = 5.675` makes coverage exactly 1.0 at `d = 5.0` and
exactly 0.0 at `d = 6.35` — the same outer extent as today's hard-ring-plus-fade, so the
border keeps its current visible weight. If it does not, that is a port bug, not a value
to tune.

Two consequences, both free:

- The 0.45 Gaussian can go. A signed DF is already sub-pixel accurate; the blur was
  compensating for a binary-mask DF, and it is what makes AA thickness inconsistent
  between flat edges and 1px tips (Pikachu ears, Sandslash spikes).
- `scrub_white_only` (§6.6) should stop firing entirely. Keep the detector, drop the
  writer, and fail the build if it triggers (§14.2).

#### Hard constraint: the gate must be geometric, never alpha-only

`back` must not extend under translucent wings, or §7.10 root cause 2 returns. **The
obvious way to prevent that does not work.** This was measured, not reasoned — see
§7.13: a `smoothstep` gate on source alpha evaluates to 0.63 at a typical wing alpha of
0.4 and lays 63% opaque black under the wings.

The reason is structural: **the opaque core's own AA fringe and a translucent wing pixel
can carry identical alpha.** No function of alpha alone separates them. The separation is
geometric — black belongs in exactly two places:

1. within roughly 1px of the core boundary (the core's own antialiasing), and
2. outside the silhouette entirely.

Nowhere else. A wing pixel 10px from the core fails both tests; a core AA pixel passes the
first. Express the gate as a distance test on `d_core` / `d_sil`, never as a threshold on
`A`.

#### Validation status — read before implementing

| Element | Status |
|---|---|
| Cause of the white line (ramp over an unbacked ring) | Reasoned from §7.12's measured profile; consistent with §7.6 |
| `STROKE_EDGE = 5.675` preserves border weight | Arithmetic only — confirm on a sheet |
| Signed-DF `back` geometry | **Tested:** fill 0.957 / 0.953 / 0.957, pad 5 / 6 / 5 on `193` / `469` / `415` |
| `back` eliminating the white line | **NOT validated** — the test image had blacked-out wings (§7.13), so its profile is meaningless |
| Wing-safe geometric gate | **Unsolved.** Specified above, untested |

Do not rebuild the pack on this. Prototype on `25` / `649` / `931` for the line and
`193` / `469` / `415` for the wings, and check both against §14.2 first.

---

## 7. Chronology of problems, failures, and fixes

### 7.1 Initial outline packs (succeeded, then superseded)

| Attempt | Result |
|---|---|
| `kbtbc/wwm-outline-uicons` | Inset 2px outline + sat punch on wwm sizes; some folders left original. |
| `be5be68` bigfun 3px from PokeMiners | First full outlined UIcons tree (~22k PNGs). |
| Variant / costume gaps | Fixed in `902f7ad`, `c3a0400` (costumes 67–85, Gigantamax `_b2`). |

### 7.2 Shadow aura missing / wrong (failed → fixed)

- Early 256 work sometimes shipped `_a1` **without** purple smoke (pipeline not applied to production).  
- Restoring wwm baked `_a1` was a temporary path (`d66eab3`) then **rejected** as policy: build our own wash + `shadow_icon`.  
- Smoke scale tuned to ~1.12× to match TiMXL fill; may touch canvas edge.

### 7.3 93×93 “match TiMXL” rebuild (failed as end state)

- `b0504ce`: resized Pokémon to **93×93** to match TiMXL outline packs.  
- Kelly rejected upscaling / living at 93 when **native 256** exists. Quality first.  
- Direction locked: rebuild Pokémon to **256×256** squares from PokeMiners.

### 7.4 Sample-driven one-offs vs whole-set lock (process failure)

- Iterating only on Pikachu ears produced regressions elsewhere.  
- **Rule:** lock one pipeline; prove it on a **mixed** sheet (small tips, wide wings, Shadow, mega, large fills) before full rebuild.

### 7.5 Tip clipping vs invisible pad (QA failure)

- Ear/wing tips looked clipped; pad was increased but compare sheets were **cropped to art**, erasing the empty border.  
- **Fix:** always show true full canvas. Stroke-safe pad ≥ 5 (earlier trials used ≥ 7 during 4px stroke era).

### 7.6 Soft AA on both sides → white inner fringe (failed)

- Softening the body/stroke join with ordinary soft alpha created a **white/light hairline** inside the black border.  
- **Fix (live):** soft **outer** AA only; hard inner body cut + `scrub_white_only`.  
- **Next refinement (proto):** coverage ramp into black (`aa_in`) — see §7.10.

### 7.7 First full 256 rebuild incomplete (`00f4401`)

- 17,116 ok / **1,045 skip** (resolver missed species without `_00` natives).  
- Leftover rebuild `1af45a1` brought pack to uniform 256 (18,161 Pokémon PNGs).

### 7.8 1-alpha fringe crop bug → tiny sprites (`137a152`)

- Symptom: Inkay `686` and others tiny, thick-looking border.  
- Cause: `getbbox()` on raw alpha included 1-alpha fringe ≈ full canvas.  
- **Fix:** crop on `alpha > 20`. Pushed `137a152`.

### 7.9 Wrong / low-res source for form variants (failed → fixed)

- Squawkabilly `931_f2986` etc. looked like upscaled 93 / wrong art.  
- **Fix:** map to PokeMiners Addressable 256 originals by proto/form; rebuild (`d0d4cda`).  
- Lesson: PokeMiners has the files under **different names**; investigate, don’t substitute.

### 7.10 Translucent wing chop (partially fixed in script; pack push may lag)

| Species | Issue |
|---|---|
| Yanma `193`, Yanmega `469`, Combee `415` | Stroke hard-cut at 128 deleted wings; fill ~0.44. |
| Beedrill `15` | Milder. |
| Ribombee `743`, Cutiefly `742` | Same wing-cut class (not a small-Addressable ceiling — contain-fit upscales). |

**Root causes found:**

1. Silhouette / body used `alpha ≥ 128` only → wings gone, body undersized.  
2. Filling opaque black stroke **under** the whole mask made remaining wing pixels composite to near-black.  

**Direction:** silhouette `alpha > 20`; outer stroke ring; keep mid-alpha wing color; optional inner coverage AA.

### 7.11 Inner border jaggies (open refinement)

- Genesect shows clear stair-steps on the **inner** stroke edge at 3×; outer edge is already smooth.  
- Prototype: `aa_in` 0.8 / 1.25 / 1.8 coverage AA over black; light-bg check shows **no white fringe**.  
- Recommended lock: **`aa_in = 1.25`**, then full rebuild.

### 7.12 Halo audit + wing/size defect (measured 2026-09-04 against the live pack)

Per-icon metrics for all 18,161 files: `fullsweep-2026-09-04.csv` (fill, pad, mid-alpha).

Method: 18 icons pulled from `main`, plus a sweep of every base-form dex 1–1025.
Tool: `icondiag.py`. Every number below is reproducible from the published pack.

**Finding 1 — the live pack has no white inner boundary.**

Radial luma profile inward from the silhouette edge, Pikachu `25`, composited on white
(`d` = px from open space, `L` = mean luma, `A` = mean alpha):

```text
d:   0.5   1.5   2.5   3.5   4.5   5.5   6.5   7.5   8.5   9.5  10.5  11.5
L:  1.00  0.87  0.31  0.03  0.00  0.00  0.00  0.33  0.69  0.72  0.75  0.77
A:  0.00  0.13  0.69  0.97  1.00  1.00  1.00  1.00  1.00  1.00  1.00  1.00
```

Monotonic black-to-body ramp, no overshoot above the body plateau, and **alpha is 1.00
from d = 3.5 inward** — there is no partial-alpha band between body and stroke. Same
across all 18 icons (halo metric 0.000–0.019 typical, max 0.044, and those residuals
trace to interior holes such as Genesect's legs, not to the join). Magenta and green
backgrounds show nothing at the join.

**Conclusion: the white boundary on the sample sheets is in the `aa_in` prototype, not in
the shipped pack.** §7.6's fix is holding. Fix it in the prototype per §6.12; do not
rebuild the pack to chase it, and do not adopt de-fringe or unpremultiply changes on the
strength of it — measurement gives no evidence for those causes in what ships.

**Finding 2 — the wing/size defect is real, shipped, and mechanically explained.**

Contain-fit sizes the sprite on `alpha > 20` (wings included); the `alpha >= 128` body
cut then deletes the wings; what remains is the body alone, at the ratio of the two
bounding boxes. Predicted fill = 0.945 × (core bbox / silhouette bbox):

| dex | src ext @>20 | src ext @>=128 | ratio | predicted fill | measured fill | pad |
|---|---|---|---|---|---|---|
| 193 | 212 | 95 | 0.448 | 0.423 | **0.457** | 59 |
| 469 | 212 | 102 | 0.481 | 0.455 | **0.441** | 62 |
| 415 | 132 | 58 | 0.439 | 0.415 | **0.445** | 71 |

All three within 0.03 of prediction. The PokeMiners sources carry 1696 / 2078 / 978
mid-alpha wing pixels; the shipped icons carry **none**. This is §7.10 root cause 1,
still live in the pack.

**Full sweep — every icon in the pack.**

18,161 icons measured (the complete `index.json` manifest), zero fetch errors, all
256×256, none empty. **92 fall below `fill = 0.88`, across 11 dex:**

| dex | name | detected | hidden `_a1` | true total | of variants | worst fill |
|---|---|---|---|---|---|---|
| 193 | Yanma | 8 | 2 | 10 | 10 | 0.457 |
| 415 | Combee | 16 | 4 | 20 | 20 | 0.445 |
| 469 | Yanmega | 8 | 2 | 10 | 10 | 0.441 |
| 743 | Ribombee | 8 | 2 | 10 | 10 | 0.664 |
| 742 | Cutiefly | 8 | 2 | 10 | 10 | 0.684 |
| 15 | Beedrill | 8 | 4 | 12 | 20 | 0.680 |
| 577 | Solosis | 8 | 2 | 10 | 10 | 0.766 |
| 738 | Vikavolt | 8 | 4 | 12 | 20 | 0.852 |
| 578 | Duosion | 8 | 2 | 10 | 10 | 0.863 |
| 751 | Dewpider | 8 | 2 | 10 | 10 | 0.871 |
| 938 | Tadbulb | 4 | 2 | 6 | 10 | 0.871 |

**120 of 18,161 icons (0.66%)**, counting the Shadow variants the metric cannot see
(§7.14).

The defect tracks the **source art, not the form.** It hits every variant that shares the
affected body art — `_s`, `_a2`, `_b1`, `_g2`, and form ids such as `738_f3317` — and
skips variants drawn from different art: `15_e1` (Mega Beedrill) is clean, `738`'s shiny
set is clean, `938`'s non-shiny set is clean. That is exactly what the mechanism predicts,
and it means the fix is **per source asset, not per filename**.

**Source verification.** Predicted fill = 0.945 × (core bbox / silhouette bbox):

| dex | src ext @>20 | @>=128 | ratio | predicted | measured | verdict |
|---|---|---|---|---|---|---|
| 193 | 212 | 95 | 0.448 | 0.423 | 0.457 | **confirmed** |
| 469 | 212 | 102 | 0.481 | 0.455 | 0.441 | **confirmed** |
| 415 | 132 | 58 | 0.439 | 0.415 | 0.445 | **confirmed** |
| 15 | 153 | 106 | 0.693 | 0.655 | 0.680 | **confirmed** |
| 743 | 105 | 72 | 0.686 | 0.648 | 0.672 | **confirmed** |
| 751 | 98 | 90 | 0.918 | 0.868 | 0.871 | **confirmed** |
| 742 | 76 | 64 | 0.842 | 0.796 | 0.750 | **confirmed** |
| 578 | 100 | 98 | 0.980 | 0.926 | 0.867 | borderline (Δ 0.059) |
| 577 | 75 | 70 | 0.933 | 0.882 | 0.789 | **unexplained** (Δ 0.093) |
| 738 | 156 | 155 | 0.994 | 0.939 | 0.852 | **unexplained** (Δ 0.087) |

`577` and `738` have core and silhouette bounding boxes that nearly coincide, so the body
cut cannot shrink them much — **something else is scaling them down.** `ensure_stroke_safe`
(§6.5) is the obvious suspect but is unconfirmed. Do not assume they are the same
defect; §14.3.

Addressable sources for `738` / `742` / `743` / `751` are `pm{dex}.icon.png` — no form
suffix, unlike the `pm{dex}.f{PROTO}.icon.png` pattern in §5 step 4.

### 7.13 Trap: an alpha-only wing gate blacks out the wings (measured — do not repeat)

A tempting way to restore the wings is to build the outer ring from the silhouette and
gate it by source alpha so black never lands under translucent pixels:

```text
wing_gate = 1 - smoothstep(A, 40/255, 190/255)
stroke_A  = max(back, ring * wing_gate)
```

**This does not work.** At a typical wing alpha of `A = 0.4` the gate evaluates to
**0.63**, laying 63% opaque black under the wings. Tested on `193` / `469` / `415`:
geometry came back correct (fill 0.957 / 0.953 / 0.957, pad 5 / 6 / 5) and the wings came
back **solid black** — precisely §7.10 root cause 2, and precisely what §6.4 already
warns against.

The reason is structural: **the opaque core's own AA fringe and a translucent wing pixel
can carry identical alpha.** Any gate parameterised only on alpha reproduces this failure.
The separation has to be geometric — see §6.12.

Recorded as a measured negative result so the next attempt starts past it.

### 7.14 The Shadow smoke hides clipped Pokémon from the size check

**The smoke is not the problem, and clipping the smoke is fine.** The problem is that the
Pokémon *inside* a Shadow icon is clipped just as badly as the base icon, and the
smoke makes the automated size check report a healthy number — so those icons never get
flagged.

`193` and `193_a1` have **identical opaque extent, 113 px**: the same chopped Yanma. But
`fill`, measured on `alpha > 20`, reads **0.457 vs 0.980**, because `shadow_icon` spreads
almost to the canvas edge and the measurement picks up the smoke's bounding box instead of
the Pokémon's:

| icon | fill @>20 | opaque extent (the Pokémon) |
|---|---|---|
| `193` / `193_a1` | 0.457 / 0.980 | 113 / 113 |
| `469` / `469_a1` | 0.441 / 0.980 | 109 / 109 |
| `415` / `415_a1` | 0.445 / 0.980 | 110 / 111 |
| `577` / `577_a1` | 0.789 / 0.980 | 198 / 199 |

**28 Shadow icons carry a clipped Pokémon and pass every geometry check.** §6.10's
rule that `_a1` is exempt from pad checks is right for *pad*, but it silently creates a
blind spot for *size*. Any size invariant must measure `_a1` on the **opaque extent**,
never on the silhouette bbox — §14.2 INV-2.

---

## 8. Confirmed form mappings (investigate, don’t guess)

### 7.15 B1 wing-cut locked and shipped (`42cc026`)

Kelly locked **option B1** with `CUT_PX = 1.0` on 2026-09-04 after a measured sweep
(0.5 / 1.0 / 1.5 / 2.0) on `25`, `193`, `469`, `415`, `15`, `742`, `743`, `751`, `555`.

```text
bodyA = 1.0           where d_core <= CUT_PX (1.0)
bodyA = source alpha  beyond that
```

Stroke: outer ring only, tiny underlap under opaque core, soft outer AA, then
`scrub_white_only`. Do not fill opaque black under the whole silhouette (§7.10 / §7.13).

Option A (fit on opaque core) remains ruled out (wingspan off canvas). Option B (stop
cutting entirely) remains rejected (unbacked body AA). Option B2 (B1 + §6.12 back layer)
stays deferred with `aa_in`.

**Pack:** full Pokémon rebuild, 18,156 ok / 5 skip (`0.png` family) / 0 err. Wing-class
mid-alpha restored (examples: Combee wingR 0.21→0.97, Ribombee 0.07→0.93, Cutiefly
0.16→0.84). `577` / `738` fills returned to stroke-safe range. Join `partial%` in the
sweep harness stayed high (~80%); do not treat an earlier "0% partial" note as production
truth.

Samples: `/workspace/uicon-samples/fx-v2/quality256/b1-cutpx/`,
`b1-locked/`, `spotcheck-prepush/`, `repo-compare/`.

---

## 8. Confirmed form mappings (investigate, don’t guess)

### Unown (201)

| Glyph | UIcons file |
|---|---|
| A–E | `201_f1` … `201_f5` |
| **F** | **`201.png`** (default; no `_f6`) |
| G–Z | `201_f7` … `201_f26` |
| ! | `201_f27` |
| ? | `201_f28` |

### Burmy (412) / Wormadam (413)

| Cloak | Burmy | Wormadam |
|---|---|---|
| Plant | `412.png` | `413.png` |
| Sandy | `412_f119` | `413_f88` |
| Trash | `412_f120` | `413_f89` |

Default-form aliases like `413_f1709` (master “Normal”) are covered by the default file — not separate art.

### Darmanitan (555) — verified

| Form | File |
|---|---|
| Standard | `555.png` |
| Zen | `555_f139.png` |
| Galarian Standard | `555_f2342.png` |
| Galarian Zen | `555_f2343.png` |

### Kyurem (646)

| Form | File |
|---|---|
| Normal | `646.png` |
| Black | `646_f147.png` |
| White | `646_f148.png` |

### Genesect (649)

| Form | File |
|---|---|
| Normal | `649.png` |
| Shock | `649_f594.png` |
| Burn | `649_f595.png` |
| Chill | `649_f596.png` |
| Douse | `649_f597.png` |

### Squawkabilly (931)

Green / Blue / Yellow / White form variants from PokeMiners 256 Addressable (not 93 upscale) — `d0d4cda`.

Other multi-form families (Deoxys, Rotom, Giratina, Shaymin, Basculin, Forces of Nature, Keldeo, Meloetta, Castform, Floette, Oricorio, Toxtricity, Zacian, Zamazenta, etc.) follow the same proto → `_f{id}` pattern via game master + `resolve_pokemon`.

---

## 9. Known remaining gaps (GO-only scope)

| Item | Status |
|---|---|
| `0.png` / `0_a1` / `0_a2` / `0_b1` / `0_b1_a2` | No PokeMiners file — leave unmatched; do not invent art. |
| Cutiefly `742` / Ribombee `743` | **Corrected:** not a permanent small-art ceiling. §6.2 contain-fits on the content bbox (no no-upscale guard — LANCZOS scales up). Measured fill matches the wing-cut prediction (Δ 0.046 / 0.024). Same defect class as Yanma; fixable per source asset. Addressable is still the correct PokeMiners source (no numbered `pokemon_icon_742_00`). |
| Wing-chop / low-fill (source-art defect) | **Still shipped broken** on main. Full sweep: **92 icons / 11 dex** below fill 0.88: `15`, `193`, `415`, `469`, `577`, `578`, `738`, `742`, `743`, `751`, `938`. Defect tracks **source art**, not form — every variant sharing that body is hit; different art (e.g. `15_e1`, `738` shiny set) stays clean. 8/10 wing-model dex confirmed vs source. §7.12. |
| `577` / `738` low fill | **Different bug** — not the body-cut model (core≈silhouette). Logged §14.3. |
| `rebuild_pokemon_256.py` | **Not in version control.** Workspace-only; no rebuild is reproducible from the repo. §2. |
| Build-time invariants | None exist. Every regression to date was caught by eye, and several shipped anyway. §14.2. |
| Inner AA (`aa_in`) | Prototyped; not full-pack applied. |
| Purified `_a2` | Secondary until Shadow is solid everywhere. |
| Home-only (~64 dex) | Minior, Eiscue, Alcremie, Calyrex, etc. — **out of scope** (not live GO / no GO art). |

---

## 10. Git milestones (main)

### 9.1 Update — gaps closed or moved (2026-09-04 evening)

Keep the table above as the morning audit. After `42cc026`:

| Item | New state |
|---|---|
| Wing-chop / low-fill class | **Closed in pack** via B1 + full rebuild (§7.15). |
| `577` / `738` low fill | **Closed in pack** by rebuild (older artifacts). Cause archaeology still welcome. |
| `rebuild_pokemon_256.py` | **Closed** — on `main` in `42cc026`. |
| Build-time invariants | **Still open** (§14.2). |
| Inner AA (`aa_in`) | **Still open** / prototype. |
| Weekly PokeMiners watcher | **New request** (§14.7). |

---

## 10. Git milestones (main)

| Commit | What |
|---|---|
| `be5be68` | 3px outlined UIcons from PokeMiners |
| `902f7ad` / `c3a0400` | Variant + costume / GMAX mapping |
| `d66eab3` | Restore Shadow aura (wwm path; later superseded by own smoke) |
| `b0504ce` | 93×93 TiMXL-size experiment |
| `00f4401` | First 256 rebuild, 5px stroke + smoke (partial skips) |
| `1af45a1` | Remaining icons → 256 |
| `137a152` | Crop fix for 1-alpha fringe |
| `d0d4cda` | Form variants from PokeMiners 256 Addressable (e.g. Squawkabilly) |
| `548492c` | Unown letters + Burmy cloaks from protos |
| `42cc026` | B1 wing-cut (`CUT_PX=1.0`), outer-ring stroke, full Pokémon rebuild (18,156), commit `rebuild_pokemon_256.py` |

---

## 11. Operating procedure (how to run a change)

1. **Identify** the symptom (tiny sprite, thick border, missing form, no smoke, white fringe, wing chop, inner jaggies).  
2. **Resolve source** with `resolve_pokemon` — print path + tag; open the PokeMiners file; never guess.  
3. **Prototype** on a mixed set + light/dark full-canvas sheets (+ 3× crop if edge AA).  
4. Encode the fix in `rebuild_pokemon_256.py` / `enhance_all.py` so production matches samples.  
5. Rebuild affected dexes or full pack; verify `fill` / `pad` / smoke purple pixels on `_a1`.  
6. Commit + push `main` (no force). Update this doc if policy or constants change.  
7. Ask Kelly only when actually stuck (no GO art, ambiguous proto with two valid UIcons names).

---

## 12. References

### Specs and packs
- [UIcons](https://github.com/UIcons/UIcons) — filename flags and compatibility  
- [WatWowMap/wwm-uicons](https://github.com/WatWowMap/wwm-uicons) — layout / completeness baseline  
- [kbtbc/bigfun-outline-uicons](https://github.com/kbtbc/bigfun-outline-uicons) — this pack  
- [kbtbc/wwm-outline-uicons](https://github.com/kbtbc/wwm-outline-uicons) — earlier outline experiment  

### Art and data
- [PokeMiners/pogo_assets](https://github.com/PokeMiners/pogo_assets) — `Pokemon - 256x256`, Addressable, Rocket `shadow_icon`  
- Game master JSON used locally as `master-latest.json` — form ids and protos  
- TiMXL / uicons-outline packs — visual reference for canvas fill and Shadow density (not a source to upscale)

### Credits (also in README)
- PokeMiners, WatWowMap/wwm-uicons, UIcons (nileplumb / jms412 as checklist), Mygod, whitewillem  

### Local artifacts
- `rebuild_pokemon_256.py` — locked Pokémon rebuild  
- `wwm-uicons/enhance_all.py` — indexing, `resolve_pokemon`, `enhance_rgba`  
- `/workspace/uicon-samples/fx-v2/quality256/` — compare sheets (`wingfix-*`, `inner-aa-*`, `audit-*`)
- `icondiag.py` — halo audit (radial profile), geometry metrics, dark/light/magenta/green sheet  

### Image-processing concepts used
- Premultiplied vs straight alpha compositing (Pillow `alpha_composite`)  
- Euclidean distance transform for rounded outline expansion  
- Contain-fit scaling (LANCZOS) with explicit stroke-safe margins  
- Alpha thresholding for robust bbox (`> 20` vs raw `getbbox`)  
- Coverage-based edge AA into black (inner) vs DF fade (outer)  

---

## 13. Non-negotiables (Kelly)

1. Quality and consistency first.  
2. Never upscale 93 when PokeMiners 256 exists.  
3. Never guess mappings or offer guessing as an option.  
4. Investigate from source data; ask only if stuck.  
5. Samples must not regress vs earlier good prototypes.  
6. Pokémon GO only — ignore Home-only species.  
7. Show full-canvas truth; don’t hide pad with cropped sheets.

---

## 14. Improvement backlog

§14.1–14.3 are justified by the 2026-09-04 audit (§7.12). The rest are proposals and are
labelled as such.

### 14.1 Commit `rebuild_pokemon_256.py` (verified gap, §2)

The production script is in no repo. Nothing about the pack is reproducible, reviewable,
or revertible without it, and a mixed-version pack cannot be diagnosed after the fact.
This is a prerequisite for everything else here.

While doing it, stamp each output PNG with a `tEXt` chunk carrying pipeline version,
parameter hash, and source path — then "which version built this icon?" is a script
rather than archaeology.

### 14.2 Build-time invariants

**Status (2026-09-04 evening):** script committed and pushed in `42cc026`. The `tEXt`
provenance stamp is still outstanding.

### 14.2 Build-time invariants over a committed golden set (justified by §7.12)

The wing defect is documented in §7.10 and was still live in the pack when measured.
Prose warnings cannot fail a build; assertions can.

| ID | Invariant | Catches |
|---|---|---|
| INV-1 | Mid-alpha pixel count ≥ 60% of source's, scaled for resize | §7.10 / §7.12 wing chop |
| INV-2 | `fill` in `[0.90, 0.97]`, `pad ≥ 5`. On `_a1`, measure **opaque extent**, not silhouette bbox | §7.8, §7.12, §7.14 |
| INV-3 | Mean hue of translucent regions within 10° of source | §7.13 blacked-out wings |
| INV-4 | Radial luma profile monotonic from stroke floor to body plateau | white inner boundary, any cause |
| INV-5 | No pixel with `0 < A < 255` enclosed within the stroke band | partial-alpha sandwich (§6.12) |
| INV-6 | Output is neither empty nor a near-solid black blob | catastrophic mask failure |

INV-1 and INV-3 would have caught §7.10 and §7.13 respectively without relying on
anyone's judgement. INV-4 is the metric used in §7.12 and is already implemented in
`icondiag.py`.

Golden set should span sharp tips (`25`, `28`), translucent wings (`15`, `193`, `415`,
`469`), gel/bubble translucency (`577`, `578`, `751`), tiny Addressable (`742`, `743`),
high fill (`208`, `376`), multi-form (`201_f1`, `555_f139`, `649_f594`, `931`), Shadow
(`25_a1`), shiny (`25_s`). Commit the rendered sheets so a PR diff shows the visual
change. This makes §7.4's lesson mechanical instead of procedural.

### 14.3 Explain `577` and `738` (open, §7.12)

The sweep is complete and eight of the ten dex are confirmed against source. `577`
Solosis and `738` Vikavolt are not: their core and silhouette bounding boxes nearly
coincide (ratio 0.933 and 0.994), so the body cut cannot account for their size, yet they
**ship** at fill 0.789 and 0.852.

`ensure_stroke_safe` (§6.5) was the leading suspect. **Checked against the workspace
script (2026-09-04):** for both dex, after stroke + 256 crop, margins are already ≥5, so
`ensure_stroke_safe` does **not** rescale (`will_rescale=False`). Tracing `process()`
end-to-end yields fill ≈0.93–0.96 — i.e. the **current** pipeline does not reproduce the
shipped undersize. The defect is therefore in the **shipped build artifacts** (or an
older script revision), not in the live `ensure_stroke_safe` path as written today.

Still open: what exact older step produced 0.789 / 0.852. Next: log every rescale,
diff script history once committed (§14.1), and rebuild these dex to confirm the pack
matches the trace. `578` Duosion (Δ 0.059) and `938` Tadbulb (4 icons in the sweep)
should be re-checked in the same pass — same evolution / gel-blob neighborhood.


**Status (2026-09-04 evening):** pack rebuild in `42cc026` restored `577` / `738` fill to ~0.93–0.96. The older-artifact explanation stands; keep the archaeology note above for history.

### 14.4 Proposal — render-side check before any pipeline work

The map minifies these to ~48px. A non-premultiplied texture upload with `LINEAR`
filtering, or mipmaps built from straight-alpha RGB, produces a white rim regardless of
what the PNGs contain. If the consumer is ReactMap, confirm the upload flags before
attributing any halo to the pipeline. **Unverified — nobody has checked which applies.**

### 14.5 Proposal — incremental rebuild by source hash

Cache `{uicons_name: (source_path, source_sha1, params_hash)}` and skip unchanged icons.
18k icons is why full rebuilds are rare and partial states ship (§7.7, §7.10). Makes
iteration cheap enough to verify a fix pack-wide before it lands.

### 14.6 Proposal — PNG optimisation in CI

`oxipng -o4 --strip safe` typically returns 15–30% on sprite PNGs with no visual change,
across a pack downloaded per map load. Run after the `tEXt` stamp so provenance survives.

---

### 14.7 Weekly PokeMiners update watcher (requested)

Kelly asked for a weekly check of [PokeMiners/pogo_assets](https://github.com/PokeMiners/pogo_assets)
that detects new or changed Pokémon art and updates `kbtbc/bigfun-outline-uicons`
accordingly (fetch → map changed sources to UIcons names → B1 rebuild → report / push).

Not built yet as of this writing. When landing it: store last-seen source commit/hash,
prefer incremental rebuild by source path (§14.5), and notify before a blind full 18k
push unless Kelly opts into auto-push.

### 14.8 Discord / pack positioning (context, not code)

WhiteWillem `PogoAssets` disappeared. TiMXL73 `uicons-outline` is the restored
WhiteWillem-style outline lane (roundaboutluke's mirror is the same lane, not a separate
art source). WatWowMap `wwm-uicons` is a different pack (variable rectangles). Home comps
use nileplumb `PkmnHomeIcons` `UICONS_OS` 512.

Kelly posts as **BigFun**. Promo drafts stay short, unslopped, and do not roast TiMXL/Luke.
Community asks still open outside the Pokémon pipeline: rewards too large on the map
(ReactMap `styles` / `sizeMultiplier`), WebP wish list.

Compare sheets: `/workspace/uicon-samples/fx-v2/quality256/repo-compare/`
(`fullcomps_*`, `vs_timxl_*`).

---

*End of guide. When the inner-AA (`aa_in=1.25`) full rebuild lands, update §3 and §7.10
and bump the “locked” note in `rebuild_pokemon_256.py`. Before any full rebuild, settle
§14.1 (commit the script) and §14.2 (invariants) — §7.12 shows the pack can ship a
documented, already-solved defect without anyone noticing.*

**Addendum after End of guide (2026-09-04 evening).** §14.1 (commit the script) and the wing-cut pack fix (§7.15 / `42cc026`) are done. §14.2 (invariants) and `aa_in` remain before treating the pipeline as fully hardened. Prefer §0.5 for current state; keep §§0.1–0.4 as the same-day audit trail.

### 0.6 Update — public-repo contract (2026-09-04 night)

This subsection adds defects measured on origin after `42cc026`. It does not change B1 or stroke.

| Item | Measured on origin | Fix in force |
|---|---|---|
| README still said 93×93, 3px, wwm baked shadow | Yes | README matches 256 / ~5px outer ring / own smoke |
| GitHub description said "3px outline" | Yes | Description matches PokeMiners 256 + 5px + own smoke |
| `package.json` name `wwm-uicons` | Yes | `bigfun-outline-uicons` |
| Root `index.json` indexed `.git` | Yes | `.git` key removed; `index.js` skips dotdirs, `node_modules`, `scripts`, `docs`, `.cursor` |
| `rebuild_pokemon_256.py` hardcoded `/workspace` paths | Yes | `BIGFUN_OUT`, `POGO_ASSETS`, `BIGFUN_ENHANCE_DIR` (see `scripts/README.md`) |
| Public `kbtbc/wwm-outline-uicons/scripts/enhance_all.py` has no `resolve_pokemon` | Yes | Do not use it. Vendor the workspace module into `scripts/enhance_all.py`. Rebuild still cannot run from GitHub alone until that file is copied. |
| Downloads `fullsweep.csv` | Pre-B1 (Yanma fill 0.457) | Do not use as live metrics after `42cc026` |
| `aa_in` inner coverage | Still prototype | Mixed sheet before any full rebuild |
| INV-1 / INV-3 | Still none | Golden list in `scripts/golden.txt`; source-backed checks need PokeMiners |

Addressable wording: numbered PokeMiners 256 first. If none, 256 Addressable may be contain-fit scaled. Never upscale 93 / wwm / TiMXL when either 256 source exists.

Never fill opaque black under the whole silhouette. Never gate wings on alpha. Never invent wing color.

QA for the next lock: full 256 canvas, light and dark, 3x nearest inner joins, and map-size (~40-50px) on light and dark. No cropped sheets.

