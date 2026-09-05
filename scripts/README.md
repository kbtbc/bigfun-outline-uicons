# Build scripts (not UIcons)

This folder is skipped by `index.js`. Do not put PNGs here.

## resolve_pokemon

`rebuild_pokemon_256.py` imports `load_indexes`, `resolve_pokemon`, and `enhance_rgba` from `enhance_all.py`.

That module lives in the build workspace as `/workspace/wwm-uicons/enhance_all.py`. It is **not** `kbtbc/wwm-outline-uicons/scripts/enhance_all.py` (that file is the old 2px inset job and has no resolver).

Until the workspace module is copied here:

1. Place `enhance_all.py` in this folder, or
2. Set `BIGFUN_ENHANCE_DIR` to the directory that contains it.

Also set `POGO_ASSETS` to a clone of [PokeMiners/pogo_assets](https://github.com/PokeMiners/pogo_assets). Optional: `BIGFUN_OUT` to override the Pokémon output directory (default: repo `pokemon/`).

Do not invent form mappings. Do not substitute 93/wwm/TiMXL art when a PokeMiners 256 source exists.
