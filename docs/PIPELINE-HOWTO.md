# bigfun-outline-uicons pipeline how-to

**Repo:** https://github.com/kbtbc/bigfun-outline-uicons
**Raw base:** `https://raw.githubusercontent.com/kbtbc/bigfun-outline-uicons/main/`
**Owner:** Kelly Britt (`kbtbc`) / BigFun
**Scope:** Pokémon GO map icons only, UIcons-compatible. Home-only and unreleased species stay out.

This is the operating manual for the pack: what the locked pipeline is, how to run it,
how to verify it, and the traps that were found by measurement so nobody falls into them
twice. It describes what is live on `main` right now.

---

## 1. Goal and non-negotiables

Produce a high-quality, consistent UIcons Pokémon pack for GO maps.

1. Quality and consistency beat speed.
2. Source PokeMiners `Pokemon - 256x256` first. Never upscale 93px, wwm, or TiMXL art
   when a 256 source exists.
3. Never guess mappings, borrow inferior art, or invent substitutes. Investigate from
   source (game master protos, files on disk). Ask Kelly only when actually stuck.
4. One locked whole-set pipeline, proved on a mixed golden sheet, before any full rebuild.
5. The pack is not fixed until the rebuild is on `main`.
6. QA shows the full uncropped 256 canvas, light and dark, plus 3x inner joins and
   map-size (~40 to 50 px). Never cropped sheets.
7. UIcons PNG naming and per-folder `index.json` are mandatory. `0.png` placeholders stay
   unmatched. No WebP replacement.

## 2. Repo layout

| Path | What |
|---|---|
| `pokemon/` ... `raid/` etc. | The pack. UIcons folders, PNG + `index.json` each. |
| `index.js` | Regenerates every `index.json` (`node -e "require('./index').update()"`). Skips dotdirs, `node_modules`, `docs`, `tools`. |
| `tools/` | The whole pipeline. Not indexed, not part of the pack. |
| `docs/PIPELINE-HOWTO.md` | This guide. |
| `docs/qa/sheets/` | Committed QA sheets for the current lock. |
| `.github/workflows/weekly-pokeminers.yml` | Weekly new-Pokemon watcher (opens a PR, never pushes art unattended). |

### Tools

| Script | Purpose |
|---|---|
| `tools/rebuild_pokemon_256.py` | The locked rebuild. All production constants live here. |
| `tools/enhance_all.py` | Source indexing, `resolve_pokemon`, `enhance_rgba`. Vendored here; do not use the old `kbtbc/wwm-outline-uicons/scripts/enhance_all.py`. |
| `tools/_paths.py` | Shared path defaults, overridable by env. |
| `tools/golden.txt` | The 17-icon golden set. |
| `tools/fetch_golden_sources.py` | Pulls golden-set sources from PokeMiners without guessing paths. |
| `tools/qa_sheets.py` | Golden sheets (map size, canvas, 3x joins) plus INV-1 and INV-3 invariants. |
| `tools/check_wing_zone.py` | Asserts the distance-protected wing zone is byte-identical between two builds. |
| `tools/verify_pokemon_256.py` | Canvas, fill, and pad spot checks. |
| `tools/check_new_pokemon.py` | Weekly watcher core: finds newly released art the pack lacks. |
| `tools/audit_coverage.py` | Master-walk audit: every master form, costume, gender variant, and shiny either has a pack file or is explained. Run after resolver changes and alongside the watcher. |
| `tools/audit_sources.py` | Source-exhaustive audit (the reverse direction): every PokeMiners 256 file must be used by some pack file or explained. Catches art that rides no master field: Gigantamax and Urshifu bread modes, Primal. Fails on REAL-GAP. |
| `tools/sync_resolve.py` | Resolve-drift guard. `tools/resolve-manifest.json` records the source each pack file was built from; this rebuilds any file whose resolution changed. Closes the base-copy hole: a form registered in the master before its art ships (Pikachu Glass Helmet 2026) gets upgraded to real art automatically the week PokeMiners exports it. |
| `tools/check_public_contract.py` | README, `package.json`, root `index.json` sanity (no `.git` key, UIcons folder set). |

### Environment

| Var | Meaning | Default |
|---|---|---|
| `POGO_ASSETS` | PokeMiners clone root (contains `Images/`) | `/workspace/pogo_assets` |
| `MASTER_JSON` | Game master (WatWowMap Masterfile-Generator `master-latest.json`) | `/workspace/master-latest.json` |
| `BIGFUN_OUT` | Output folder | repo `pokemon/` |
| `BIGFUN_WORKERS` | Rebuild processes | 4 |
| `BIGFUN_AA_IN` | Inner AA ramp px. Locked default 1.25; `0` reproduces the 42cc026 B1 pack | 1.25 |
| `BIGFUN_POCKET_FILL` | Enclosed-pocket rule. Locked default 1; `0` reproduces 42cc026 | 1 |

## 3. Locked constants

Production constants in `tools/rebuild_pokemon_256.py`. Do not change any of these
except through a new mixed-sheet lock with Kelly.

```text
CANVAS       = 256     # square, contain-fit, aspect preserved
STROKE_PX    = 5.0     # outer ring width
AA_OUT       = 1.35    # soft fade outside the ring
CUT_PX       = 1.0     # B1: harden body alpha within this distance of the opaque core
SIL_THR      = 20      # silhouette / mid-alpha keep threshold (alpha > 20)
SOLID_THR    = 128     # opaque core threshold (alpha >= 128)
STROKE_SAFE  = 5       # minimum empty pad after stroke; smoke may still hit the edge
SMOKE_SCALE  = 1.12    # shadow_icon size vs canvas
AA_IN        = 1.25    # inner join ramp (locked 2026-09-04)
POCKET_FILL  = 1       # enclosed faint-art pockets keep source alpha (locked 2026-09-04)
```

The saturation punch in `enhance_rgba` is intentional and equally locked.

## 4. UIcons filename grammar

```text
{dex}[_b{bread}][_e{evo}][_f{form}][_c{costume}][_g{gender}][_a{alignment}][_s].png
```

| File | Meaning |
|---|---|
| `25.png` / `25_s.png` | Pikachu, shiny |
| `25_a1.png` / `25_a2.png` | Shadow, Purified |
| `6_e2.png` / `6_e3.png` | Mega X, Mega Y (proto temp-evo ids; `_e1` = plain Mega, kept as an X compatibility copy on dual-mega species) |
| `382_e4.png` | Primal Kyogre (temp-evo id 4) |
| `12_b2.png` | Gigantamax Butterfree (bread id 2; `_b1` Dynamax uses base art by design) |
| `892_b2.png` / `892_b3.png` | Urshifu single / rapid strike GMAX (source tokens `BREAD_DOUGH_MODE` / `_2`, hue-matched against wwm) |
| `555_f139.png` | Darmanitan Zen (form id 139) |
| `201_f1.png` | Unown A |
| `415_g2.png` | Combee female |

Evolution and bread ids come from the game protos (maps send them raw through
uicons.js): e1 Mega, e2 Mega X, e3 Mega Y, e4 Primal; b1 Dynamax, b2
Gigantamax, b3 second GMAX style (Urshifu only). Do not renumber from pack
conventions: wwm ships X/Y at e1/e2 and lacks e3 entirely, which is a trap.

Alignment variants share body art with the base name; the aura is applied in `process()`.

## 5. Source resolution

Implemented in `enhance_all.resolve_pokemon`. Order:

1. Parse the UIcons name into dex, form, costume, evo, gender, shiny, alignment.
2. Build form tokens from the game master proto first (`UNOWN_A`, `DARMANITAN_ZEN`),
   then aliases.
3. Prefer numbered `Pokemon - 256x256`: `pokemon_icon_{ddd}_{form}_{costume}[_shiny].png`.
   The numbered base `_00` file is only a candidate when **no** form and no female
   variant was requested. This is load-bearing: species with both a numbered base and
   Addressable form art (Spinda patterns, Hisuians, goggles Charmander) or Addressable
   `.g2` art (female Eevee) silently got base art before the 2026-09-05 fix.
4. Else 256 Addressable: `pm{dex}[.f{PROTO}][.c{N}][.g2][.s].icon.png` under
   `Pokemon - 256x256/Addressable Assets/`. Contain-fit may scale this art up.
5. Never fall back to low-res sources when either 256 source exists.

**A form must never silently resolve to the default species art.** The resolver
returns a miss for a form request with no art of its own. Since 2026-09-05 every
non-default master form still ships a file (maps can tell Spinda patterns and
Scatterbug regions apart): forms with their own art build from it, forms without
build as **explicit base-art copies** through `worker(name, key={dex}.png)`. The
copy is deliberate and keyed on the base name; nothing resolves silently.

Female art lives in three places, all covered: the numbered `_01` slot (older
gens), bare Addressable `.g2` (Frillish, Meowstic, Pyroar, Eevee line), and
form/costume+`.g2` combos (costume Pikachu). ReactMap and Diadem request
`_g2` names through uicons.js; missing files fall back to base, so a shipped
`_g2` is strictly additive.

### Confirmed form mappings

| Family | Mapping |
|---|---|
| Unown 201 | A to E are `201_f1` to `201_f5`, **F is `201.png`** (no `_f6`), G to Z are `201_f7` to `201_f26`, `!` is `201_f27`, `?` is `201_f28` |
| Burmy 412 / Wormadam 413 | Plant is the base file; Sandy `412_f119` / `413_f88`; Trash `412_f120` / `413_f89`. Master "Normal" aliases like `413_f1709` are covered by the base file |
| Darmanitan 555 | Zen `555_f139`, Galarian `555_f2342`, Galarian Zen `555_f2343` |
| Kyurem 646 | Black `646_f147`, White `646_f148` |
| Genesect 649 | Shock `649_f594`, Burn `649_f595`, Chill `649_f596`, Douse `649_f597` |
| Squawkabilly 931 | Plumage forms from 256 Addressable, never 93px upscale |

Note: some Addressable sources carry no form suffix at all (`pm742.icon.png`,
`pm743.icon.png`). Other multi-form families follow the same proto to `_f{id}` pattern
through the game master.

## 6. The pipeline, stage by stage

Stack: Python 3, Pillow, NumPy. The Euclidean distance transform (EDT) is pure NumPy,
Felzenszwalb-Huttenlocher two-pass, no SciPy. Parallel rebuild via `ProcessPoolExecutor`.

### 6.1 Crop and contain-fit

PokeMiners 256 sprites carry a near-invisible 1-alpha halo. `getbbox()` on raw alpha
returns nearly the full frame, which shipped tiny sprites with huge-looking borders.
**Always crop and measure on `alpha > 20`.**

```text
target = CANVAS - 2*(STROKE_PX + AA_OUT + STROKE_SAFE)
scale  = min(target/w, target/h)      # contain-fit, LANCZOS, upscales small art too
```

### 6.2 Enhance

`enhance_rgba` applies the saturation and clarity punch on the RGBA sprite before any
stroke work.

### 6.3 Masks and the pocket rule

```text
sil   = alpha > SIL_THR      # silhouette, includes translucent wings
solid = alpha >= SOLID_THR   # opaque core
```

With `POCKET_FILL=1` the background is defined by connectivity, not by threshold alone:
a flood fill from the canvas border marks the true outside. The outer ring only draws
there. An enclosed sub-threshold pocket that contains faint art (alpha 2 to `SIL_THR`,
the Solosis gel class) keeps the source's faint alpha and gets no ring. A truly empty
enclosed hole still gets the ring. Open gaps such as wing lattices connect to the border
and behave exactly as before.

Why: Solosis has an 857 px pocket of alpha 4 to 20 gel fully enclosed inside the
silhouette. Threshold-only logic classified it as background and drew outline scribbles
inside the face. Morphological closing cannot fix this (radius 2 cannot span the pocket;
larger radii and Gaussian silhouettes blur the icon through the stroke-safe rescale or
re-render wing lattices).

### 6.4 Outer stroke

Rounded EDT expansion, never a square `MaxFilter` dilate (blocky tips):

```text
ring: 0 < dist_outside(sil) <= STROKE_PX          -> black, alpha 255
band: STROKE_PX < dist <= STROKE_PX + AA_OUT      -> alpha fades 255 to 0
```

plus a light Gaussian (~0.45) on the stroke alpha, stroke RGB forced pure black, and
`scrub_white_only` afterwards for stray bright fringe pixels (it only touches neutral
low-luminance stroke neighborhoods, never colored wing pixels).

**The stroke is an outer ring only, plus a tiny underlap under the opaque core.** Never
fill black under the whole silhouette: translucent wings composite against it and turn
muddy black.

### 6.5 Body alpha: B1 plus the locked inner AA

B1 (the wing-keep rule): harden body alpha to 255 within `CUT_PX` of the opaque core;
keep the source's mid-alpha everywhere beyond. This preserves translucent wings (Yanma,
Yanmega, Combee, Beedrill, Cutiefly, Ribombee) while keeping the core edge solid.

`AA_IN=1.25` (locked) smooths the stair-stepped inner join between body and ring:

- A signed-distance ramp raises body alpha near the core boundary so the inner edge
  resolves with sub-pixel coverage instead of a hard staircase.
- The stroke layer gets an opaque black backing under the ramp zone, so the ramp always
  blends into black, never into the map tile. **Total alpha stays 255 across the join at
  any tile color; no white hairline can form by construction.**
- Both the ramp and its backing are gated on distance to the opaque core AND distance to
  the silhouette edge. Interior boundaries (Solosis nucleus), fine details (Farfetch'd),
  and wing membranes stay exact B1 / source alpha. The affected zone is a band of about
  2 px at the outer body edge.

### 6.6 Stroke-safe pad

After cropping back to 256, `ensure_stroke_safe` rescales and recenters if any content
margin at `alpha > 20` is under `STROKE_SAFE`. Smoke is exempt and may touch the edge.

### 6.7 Reward icon normalization

Reward icons inherited Niantic's inconsistent source padding (Poke Ball filled 99%
of canvas, Great/Ultra 84%), which renders as visibly different sizes at equal
marker size. Locked 2026-09-06, applied by `tools/normalize_rewards.py`:
`reward/item`, `candy`, `xl_candy`, `pokecoin` contain-fit to **0.85** max-extent
(round objects read optically larger, and stacked-amount variants need edge room);
`reward/mega_resource`, `stardust`, `experience` to **0.99**. The tool is
idempotent (skips files within 0.02 of target) and measures the content box at
`alpha > 2`, not the pipeline's 20, because faint item glows drift below 20 after
a resize and would otherwise re-trigger on every run. Run it after adding any new
reward icons. Do not normalize `gym` (size encodes trainer occupancy), `weather`
(intentional composition), `raid/egg` (glow auras inflate the bbox), or `misc`
(heterogeneous symbols).

### 6.8 Shadow and Purified

`_a1`: purple body wash (lerp toward `(95, 30, 160)`, ~0.22 strength, right-biased),
then the normal stroke pipeline, then PokeMiners `Rocket/shadow_icon.png` composited
**on top, last**, at `SMOKE_SCALE=1.12`, opacity ~0.95, offset slightly right and up.
Never copy wwm's baked `_a1`.

`_a2`: same body pipeline, no smoke.

## 7. Traps, all found by measurement

Each of these was tried or shipped and failed. Do not repeat them.

1. **Alpha-only wing gates black out wings.** A `smoothstep` gate on source alpha
   evaluates to 0.63 at typical wing alpha 0.4 and lays 63% black under the membrane.
   The opaque core's own AA fringe and a wing pixel can carry identical alpha; no
   function of alpha alone separates them. Gate on distance, always.
2. **Black under the whole silhouette kills wings** (composites them to near-black).
   Ring plus tiny core underlap only.
3. **Soft AA on both sides of the ring leaves a white inner hairline.** Soft outer only;
   the inner side needs opaque black underneath it (that is what the AA_IN backing is).
4. **An unbacked inner ramp reintroduces the hairline.** `body_A < 255` over
   `stroke_A < 255` means total alpha under 255 and the tile shows through. The ramp
   must sit on the signed-DF black backing.
5. **Raw `getbbox()` crops on the 1-alpha halo** and ships tiny sprites. Crop at
   `alpha > 20`.
6. **The smoke hides clipped Pokémon from size checks.** `193_a1` measured fill 0.98
   while carrying the same chopped Yanma as the 0.46-fill base icon. Measure `_a1` size
   on the opaque extent, never the silhouette bbox.
7. **Silent form fallback ships duplicate art under form names.** Only build a form file
   when its resolved source differs from the base resolve.
8. **Cropped QA sheets hide the pad** and make healthy tips look clipped. Full canvas
   always.
9. **Upscaling TiMXL 93px to 256 for comparisons makes it look soft** and flatters us.
   Compare at map size and at native, side by side.
10. **Iterating on one species regresses others.** Prove every pipeline change on the
    mixed golden sheet before rebuilding anything.
11. **Prose cannot fail a build.** The wing chop was documented and still shipped.
    Invariants below are the guard.

## 8. QA and invariants

### Golden set

`tools/golden.txt`, 17 icons: sharp tips (25, 28), translucent wings (15, 193, 415,
469, 742, 743), gel translucency (577), multi-form (555_f139, 649, 931), Shadow (25_a1,
83_a1), shiny (25_s), plus 555 and 83 controls.

### Procedure for any pipeline change

1. Fetch sources: `python tools/fetch_golden_sources.py` (uses GitHub tree listings,
   no guessed paths), or a sparse clone of PokeMiners (see §9).
2. Build the golden set to a scratch folder (`BIGFUN_OUT`), flags as intended.
3. `python tools/qa_sheets.py`: renders map-size light/dark, canvas-256 light/dark, and
   3x nearest inner-join sheets, and prints the invariants:
   - **INV-1**: mid-alpha pixel count at least 60% of the source's (wings survived).
   - **INV-3**: mean hue of translucent regions within 10 degrees of source (wings kept
     their color; measured on a consistent mask to avoid sampling artifacts).
4. `python tools/check_wing_zone.py old_dir new_dir`: wing-zone pixels (far from the
   opaque core, mid-alpha) must be byte-identical when the change should not touch wings.
5. Hairline check: composite on white, radial luma profile inward across the join must
   ramp monotonically from body to stroke floor with alpha 1.0 throughout the join band.
6. Kelly reviews the sheets. Only then rebuild the full set.

### Full-set checks after a rebuild

- Count: 18,161 files, `ok=18,156 skip=5 err=0` (the 5 are the `0.png` placeholder family).
- Every output exactly 256x256.
- Fill 0.93 to 0.96 and pad >= 5 on spot dexes (`tools/verify_pokemon_256.py`); `_a1`
  measured on opaque extent.
- `node -e "require('./index').update()"` if any filenames were added or removed;
  root `index.json` must not contain `.git` or `tools`.
- `python tools/check_public_contract.py` before pushing.

## 9. Running a rebuild

```powershell
# sources (sparse clone, ~150 MB)
git clone --depth 1 --filter=blob:none --sparse https://github.com/PokeMiners/pogo_assets .cache/pogo_assets
cd .cache/pogo_assets; git sparse-checkout set "Images/Pokemon - 256x256" "Images/Rocket"; cd ../..
curl -o .cache/master-latest.json https://raw.githubusercontent.com/WatWowMap/Masterfile-Generator/master/master-latest.json

$env:POGO_ASSETS = "$PWD\.cache\pogo_assets"
$env:MASTER_JSON = "$PWD\.cache\master-latest.json"
$env:BIGFUN_WORKERS = "12"

# full pack (~30 min at 12 workers)
python tools/rebuild_pokemon_256.py

# specific dexes
python tools/rebuild_pokemon_256.py 193,415,469
```

The rebuild iterates the existing filenames in `pokemon/`, so it never invents names and
never drops files. Icons whose source does not resolve are skipped and left untouched.

## 10. Weekly PokeMiners watcher

`.github/workflows/weekly-pokeminers.yml` runs Monday 09:00 UTC and on manual dispatch:
sparse-clones PokeMiners, fetches the game master, runs
`tools/check_new_pokemon.py --build`, regenerates `index.json`, and **opens a pull
request** with the report. It never pushes art to `main` unattended.

The watcher builds names by §5 rules: the species or form must be in the game master
and the species must have GO art. Forms with their own art build from it; forms
without build as explicit base-art copies. It also detects new female art (numbered
`_01` and bare Addressable `.g2`). New names get the full family: base, `_s`, `_a1`,
`_a1_s`, `_a2`, `_a2_s`, with every shiny variant gated on shiny source art
resolving. The workflow then runs `tools/audit_coverage.py` and appends the report,
which also catches form/costume+female combos the watcher does not scan. Anything
that errors lands in a NEEDS-REVIEW list in the PR body for a human.

## 11. Device cache extraction (Android)

Proven 2026-09-05: icons can be harvested from a phone before PokeMiners publishes,
or to verify a texture at the source. The 78 icons pulled this way matched
PokeMiners' copies pixel-for-pixel within one encoder rounding step, so this route
is trustworthy when it is the only one available.

Requirements: any phone on **Android 10 or older** (Android 11+ locks
`/sdcard/Android/data`; root would then be needed and GO blocks rooted devices),
Pokémon GO installed and logged in, USB debugging on, `adb`, `pip install UnityPy`.

1. Snapshot the bundle cache:
   `adb shell ls /sdcard/Android/data/com.nianticlabs.pokemongo/files/UnityCache/Shared/ > before.txt`
2. On the phone, render the target sprite. The Pokédex form/costume gallery is the
   reliable trigger: every icon shown on screen downloads its bundle.
3. Diff the listing against `before.txt`; each new directory is one bundle
   (names are opaque hashes, so the timestamp diff is the only reliable mapping).
4. `adb pull` the new directories and load each `__data` file with UnityPy. Icon
   textures are `Texture2D`/`Sprite` objects named in PokeMiners' Addressable
   convention (`pm25.fVISOR_2026.g2.s.icon`), 256x256, ready for the source tree.

The live asset catalogs sit next to the cache in
`files/com.unity.addressables/` (`catalog_pkmn` variant carries every Pokémon
bundle name). The CDN base URL is server-issued per session and never touches
disk, so direct downloads are not possible; the render-then-pull loop is the way.
A decrypted app bundle (IPA/APK) contains no Pokémon icons: only local UI bundles
and the il2cpp metadata (useful to confirm which form enums a client knows).

## 12. Positioning and community

History, for honest promo copy: WhiteWillem's outline pack died with his repos. TiMXL73
restored that lane from the same 93px-era art. This pack is the maintained PokeMiners
improvement: native 256 sources, square canvas, real `shadow_icon` smoke on `_a1`,
translucent wings preserved, consistent outline.

Kelly posts as **BigFun**. Drafts stay short, friendly, honest, and never roast TiMXL or
Luke. Do not post to Discord unless Kelly asks.

Credits: PokeMiners, WatWowMap/wwm-uicons, UIcons (nileplumb / jms412 as checklist),
Mygod, whitewillem.

## 13. Change policy

- Locked constants (§3) change only through a new golden-sheet lock approved by Kelly.
- Any join or stroke change must pass §8 before a full rebuild.
- README, GitHub description, and `package.json` must always match what is on `main`.
- This guide describes the current pipeline. Keep it current; keep discovered methods
  and measured traps; do not let it grow back into a diary.
