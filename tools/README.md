# tools — live bigfun-outline-uicons pipeline

Current production scripts only. Old 3px / one-off inspect scripts are not here.

## Requirements

- Python 3 with `Pillow`, `numpy`
- Local [PokeMiners/pogo_assets](https://github.com/PokeMiners/pogo_assets) checkout
- `master-latest.json` (game master) for form/proto resolution

Env overrides (optional):

| Env | Default |
|---|---|
| `POGO_ASSETS` | `/workspace/pogo_assets` |
| `MASTER_JSON` | `/workspace/master-latest.json` |
| `WWM_SRC` | `/workspace/wwm-uicons/src` (legacy fallback inside `enhance_all`) |

## Scripts

| Script | What it does |
|---|---|
| `enhance_all.py` | Source resolver (`resolve_pokemon`), indexes, `enhance_rgba` saturation punch |
| `rebuild_pokemon_256.py` | **Main rebuild.** 256 canvas, B1 body alpha (`CUT_PX=1.0`), outer-ring stroke, Shadow smoke |
| `rebuild_leftovers_256.py` | Rebuild pack icons that still resolve poorly / leftover sizes through the same 256 pipeline |
| `rebuild_proto_forms.py` | Rebuild Unown / Burmy / Darmanitan / Kyurem / Genesect set after proto mapping changes |
| `verify_pokemon_256.py` | Spot-check canvas is 256 and print fill/pad for sample dexes |
| `verify_proto_forms.py` | Check proto-mapped formes resolve to expected PokeMiners tags |
| `_paths.py` | Shared repo / asset path defaults |

## Usual commands

From repo root:

```bash
# full Pokémon rebuild (B1)
python3 tools/rebuild_pokemon_256.py

# one or more dex families
python3 tools/rebuild_pokemon_256.py 15,193,415,469

# verify samples
python3 tools/verify_pokemon_256.py
```

Root `rebuild_pokemon_256.py` is a thin wrapper that calls `tools/rebuild_pokemon_256.py`.

Locked constants and procedure: see `PIPELINE-HOWTO.md` (local) / project notes. Production lock: B1, `CUT_PX=1.0`, commit `42cc026`.
