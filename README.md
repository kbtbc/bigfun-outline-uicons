## bigfun outline UIcons

UIcons-compatible Pokémon GO outline pack. Pokémon icons are rebuilt from PokeMiners `Pokemon - 256x256`. Addressable 256 is used when no numbered 256 file exists. Same filenames, folders, and UIcons flags as WatWowMap/wwm-uicons.

Fully [UICONS](https://github.com/UIcons/UIcons) compatible.

**This is the lossless WebP branch**: pixel-identical to `main`, ~30% smaller downloads. Raw URL:
https://raw.githubusercontent.com/kbtbc/bigfun-outline-uicons/webp/

PNG original on [`main`](https://github.com/kbtbc/bigfun-outline-uicons):
https://raw.githubusercontent.com/kbtbc/bigfun-outline-uicons/main/

# Coverage
- Pokémon: numbered PokeMiners 256 first, then 256 Addressable (contain-fit may scale that Addressable art). wwm fallback only if no GO art exists.
- Every released form, costume, and regional variant with its own GO art: Spinda patterns, Scatterbug regions, Alolan/Galarian/Hisuian/Paldean, Mega/Primal `_e`, Gigantamax `_b`, and female `_f` icons where the art differs (Pikachu, Raichu, ...).
- Shadow `_a1`: purple body wash plus PokeMiners `shadow_icon` on top. Not copied from wwm baked `_a1`.
- Purified `_a2`: same body pipeline, no smoke.
- Reward item/mega `_aN` amounts, weather day/night, raid egg `_ex`, pokéstop `_p1-3`, extra invasion IDs from the UIcons spec / other packs.
- `0.png` placeholders stay unmatched. Home-only unreleased species are out of scope.

# Formatting
- Pokémon icons are **256×256** squares (contain-fit, aspect preserved, stroke-safe pad ≥5).
- Outer black stroke ~5px with soft outer AA. Translucent wings keep source mid-alpha (B1, `CUT_PX=1.0`).
- Smooth inner join: signed-distance inner AA (`AA_IN=1.25`) backed by solid black, so there is no stair-stepping and no white hairline on any tile color.
- Enclosed faint-art pockets (Solosis-class gel) keep the source art instead of getting outlined.
- Saturation punch is intentional.
- Reward icons are size-normalized so equal marker size means equal visual size: items, candy, XL candy, and coins contain-fit to 85% of canvas; mega resources, stardust, and XP to 99%.
- Other folders keep prior sizes (typically 96×96 from UIcons/wwm). No outline on background and spawnpoint.

# Maintenance
- The full pipeline lives in `tools/` (see `docs/PIPELINE-HOWTO.md`).
- A weekly GitHub Action checks PokeMiners for newly released Pokémon and opens a pull request with freshly built icons.
- Merging that PR (or any icon change on `main`) automatically rebuilds and force-pushes the `webp` branch, so both stay in sync.

# Image Credits
- [PokeMiners](https://github.com/PokeMiners/pogo_assets)
- [WatWowMap/wwm-uicons](https://github.com/WatWowMap/wwm-uicons)
- [UIcons](https://github.com/UIcons/UIcons) (nileplumb / jms412 packs used as a completeness checklist)
- [Mygod](https://github.com/Mygod)
- [whitewillem](https://github.com/whitewillem)
