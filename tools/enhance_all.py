#!/usr/bin/env python3
"""PokeMiners source resolver and enhance helpers for bigfun-outline-uicons.

Provides load_indexes, resolve_pokemon, enhance_rgba. Used by rebuild_pokemon_256.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

SATURATION = 1.40
CONTRAST = 1.10
BRIGHTNESS = 1.08
STROKE = 3
SKIP_OUTLINE = {"background", "spawnpoint"}

from _paths import REPO_ROOT, POGO_ASSETS, MASTER_JSON, WWM_SRC
WWM = WWM_SRC
MINERS = POGO_ASSETS / "Images"
OUT = REPO_ROOT
MASTER = json.loads(MASTER_JSON.read_text())
ADDR = MINERS / "Pokemon" / "Addressable Assets"
PX256 = MINERS / "Pokemon - 256x256"

UICONS_POKE = re.compile(
    r"^(\d+)(?:_b(\d+))?(?:_e(\d+))?(?:_f(\d+))?(?:_c(\d+))?(?:_g(\d+))?(?:_a(\d+))?(_s)?\.png$"
)

# ---------- index miners files ----------
def index_files(root: Path) -> dict[str, Path]:
    out = {}
    if not root.exists():
        return out
    for p in root.rglob("*"):
        if p.suffix.lower() == ".png":
            out[p.name] = p
            out[p.name.lower()] = p
    return out

ADDR_BY_NAME = {}
PX256_BY_NAME = {}
ITEMS_BY_NAME = {}
ALL_MINERS = {}


def load_indexes():
    global ADDR_BY_NAME, PX256_BY_NAME, ITEMS_BY_NAME, ALL_MINERS
    ADDR_BY_NAME = index_files(ADDR)
    PX256_BY_NAME = index_files(PX256)
    ITEMS_BY_NAME = index_files(MINERS / "Items")
    ALL_MINERS = {}
    for folder in MINERS.iterdir() if MINERS.exists() else []:
        ALL_MINERS.update(index_files(folder))


# Addressable: pm{dex}(.fX)(.cY)(.g2)(.s).icon.png
ADDR_PARSE = re.compile(
    r"^pm(\d+)(?:\.f([^.]+))?(?:\.c([^.]+))?(?:\.g(\d+))?(?:\.s)?\.icon\.png$"
)


def addr_key(dex, form=None, costume=None, gender=None, shiny=False):
    parts = [f"pm{dex}"]
    if form:
        parts.append(f"f{form}")
    if costume:
        parts.append(f"c{costume}")
    if gender and str(gender) not in ("", "0", "1", "None"):
        parts.append(f"g{gender}")
    name = ".".join(parts)
    if shiny:
        name += ".s"
    return name + ".icon.png"


def form_token(dex: str, form_id: str | None) -> str | None:
    if not form_id:
        return None
    poke = MASTER["pokemon"].get(str(dex)) or {}
    default = str(poke.get("default_form_id") or "")
    if str(form_id) == default:
        return None
    forms = poke.get("forms") or {}
    info = forms.get(str(form_id)) or {}
    proto = (info.get("proto") or info.get("name") or "").upper()
    name = (poke.get("name") or "").upper().replace(" ", "_").replace("-", "_")
    if not proto:
        return None
    if proto.endswith("_NORMAL") or proto.endswith("_STANDARD"):
        return None
    for prefix in (name + "_", "POKEMON_"):
        if proto.startswith(prefix):
            rest = proto[len(prefix):]
            if rest and rest not in ("NORMAL", "STANDARD"):
                return rest
    return proto


def evo_form(dex: str, evo: str | None) -> str | None:
    """UIcons _e{id} -> source form token, ids from the TemporaryEvolution
    proto (master temp_evolutions keys): 1 MEGA, 2 MEGA_X, 3 MEGA_Y, 4 PRIMAL.
    Maps request the proto id, so Charizard/Mewtwo X/Y live at _e2/_e3.
    Legacy _e1/_e2 X/Y names are kept in the pack as compatibility copies."""
    if not evo:
        return None
    evo = str(evo)
    x = addr_key(dex, form="MEGA_X")
    if evo == "1":
        # Plain Mega; for X/Y species (no plain Mega art) keep the legacy
        # convention where _e1 showed Mega X.
        return "MEGA_X" if x in ADDR_BY_NAME else "MEGA"
    if evo == "2":
        # Proto: Mega X. Legacy trap: X/Y species used to ship Y here; for
        # single-Mega species _e2 never resolves (no MEGA_X art) and misses.
        return "MEGA_X" if x in ADDR_BY_NAME else "MEGA_Y"
    if evo == "3":
        return "MEGA_Y"
    if evo == "4":
        return "PRIMAL"
    return None


COSTUME_BY_ID = {
    1: 'HOLIDAY_2016',
    2: 'ANNIVERSARY',
    3: 'ONE_YEAR_ANNIVERSARY',
    4: 'HALLOWEEN_2017',
    5: 'SUMMER_2018',
    6: 'FALL_2018',
    7: 'NOVEMBER_2018',
    8: 'WINTER_2018',
    9: 'FEB_2019',
    10: 'MAY_2019_NOEVOLVE',
    11: 'JAN_2020_NOEVOLVE',
    12: 'APRIL_2020_NOEVOLVE',
    13: 'SAFARI_2020_NOEVOLVE',
    14: 'SPRING_2020_NOEVOLVE',
    15: 'SUMMER_2020_NOEVOLVE',
    16: 'FALL_2020_NOEVOLVE',
    17: 'WINTER_2020_NOEVOLVE',
    18: 'NOT_FOR_RELEASE_ALPHA',
    19: 'NOT_FOR_RELEASE_BETA',
    20: 'NOT_FOR_RELEASE_GAMMA',
    21: 'NOT_FOR_RELEASE_NOEVOLVE',
    22: 'KANTO_2020_NOEVOLVE',
    23: 'JOHTO_2020_NOEVOLVE',
    24: 'HOENN_2020_NOEVOLVE',
    25: 'SINNOH_2020_NOEVOLVE',
    26: 'HALLOWEEN_2020_NOEVOLVE',
    27: 'COSTUME_1',
    28: 'COSTUME_2',
    29: 'COSTUME_3',
    30: 'COSTUME_4',
    31: 'COSTUME_5',
    32: 'COSTUME_6',
    33: 'COSTUME_7',
    34: 'COSTUME_8',
    35: 'COSTUME_9',
    36: 'COSTUME_10',
    37: 'COSTUME_1_NOEVOLVE',
    38: 'COSTUME_2_NOEVOLVE',
    39: 'COSTUME_3_NOEVOLVE',
    40: 'COSTUME_4_NOEVOLVE',
    41: 'COSTUME_5_NOEVOLVE',
    42: 'COSTUME_6_NOEVOLVE',
    43: 'COSTUME_7_NOEVOLVE',
    44: 'COSTUME_8_NOEVOLVE',
    45: 'COSTUME_9_NOEVOLVE',
    46: 'COSTUME_10_NOEVOLVE',
    47: 'GOFEST_2021_NOEVOLVE',
    48: 'FASHION_2021_NOEVOLVE',
    49: 'HALLOWEEN_2021_NOEVOLVE',
    50: 'GEMS_1_2021_NOEVOLVE',
    51: 'GEMS_2_2021_NOEVOLVE',
    52: 'HOLIDAY_2021_NOEVOLVE',
    53: 'TCG_2022_NOEVOLVE',
    54: 'JAN_2022_NOEVOLVE',
    55: 'GOFEST_2022_NOEVOLVE',
    56: 'ANNIVERSARY_2022_NOEVOLVE',
    57: 'FALL_2022',
    58: 'FALL_2022_NOEVOLVE',
    59: 'HOLIDAY_2022',
    60: 'JAN_2023_NOEVOLVE',
    61: 'GOTOUR_2023_BANDANA_NOEVOLVE',
    62: 'GOTOUR_2023_HAT_NOEVOLVE',
    63: 'SPRING_2023',
    64: 'SPRING_2023_MYSTIC',
    65: 'SPRING_2023_VALOR',
    66: 'SPRING_2023_INSTINCT',
    67: 'NIGHTCAP',
    68: 'MAY_2023',
    69: 'PI',
    70: 'FALL_2023',
    71: 'FALL_2023_NOEVOLVE',
    72: 'PI_NOEVOLVE',
    73: 'HOLIDAY_2023',
    74: 'JAN_2024',
    75: 'SPRING_2024',
    77: 'SUMMER_2024',
    78: 'ANNIVERSARY_2024',
    79: 'FALL_2024',
    80: 'WINTER_2024',
    81: 'FASHION_2025',
    82: 'HORIZONS_2025_NOEVOLVE',
    83: 'ROYAL_NOEVOLVE',
    84: 'INDONESIA_2025_NOEVOLVE',
    85: 'HALLOWEEN_2025',
    86: 'SPRING_2026_A',
    87: 'SPRING_2026_B',
}

_ADDR_COSTUMES = None
_FORM_ALIASES = {
    "GALARIAN": ["GALAR"],
    "GALAR": ["GALARIAN"],
    "HISUIAN": ["HISUI"],
    "HISUI": ["HISUIAN"],
    "PALDEAN": ["PALDEA"],
    "PALDEA": ["PALDEAN"],
    "ALOLAN": ["ALOLA"],
    "ALOLA": ["ALOLA"],
}


def _addr_costumes_by_dex():
    global _ADDR_COSTUMES
    if _ADDR_COSTUMES is not None:
        return _ADDR_COSTUMES
    out = {}
    for name, path in ADDR_BY_NAME.items():
        if not name.endswith(".icon.png") or name != path.name:
            continue
        m = ADDR_PARSE.match(name)
        if not m:
            continue
        dex, form, costume, gender = m.group(1), m.group(2), m.group(3), m.group(4)
        shiny = ".s.icon.png" in name
        if costume:
            out.setdefault(dex, set()).add(costume)
    _ADDR_COSTUMES = out
    return out


def _master_form_protos(dex, form_id) -> list[str]:
    """Exact master proto strings for this UIcons form id (or default form if none)."""
    poke = MASTER["pokemon"].get(str(dex)) or {}
    forms = poke.get("forms") or {}
    fid = form_id if form_id else poke.get("default_form_id")
    if not fid:
        return []
    info = forms.get(str(fid)) or {}
    proto = (info.get("proto") or "").upper()
    if not proto:
        return []
    out = [proto]
    species = (poke.get("name") or "").upper().replace(" ", "_").replace("-", "_")
    if proto.startswith(species + "_"):
        rest = proto[len(species) + 1 :]
        if rest:
            out.append(rest)
    return out


def _form_tokens(dex, form_id, bread, evo):
    tokens = []
    eform = evo_form(dex, evo)
    if eform:
        tokens.append(eform)
    if bread == "2":
        # Gigantamax. Urshifu's two GMAX styles ship as BREAD_DOUGH_MODE
        # tokens: MODE = single strike (red, _b2), MODE_2 = rapid strike
        # (blue, _b3). Hue-matched against wwm's field-tested 892_b2/_b3.
        tokens.append("GIGANTAMAX")
        tokens.append("BREAD_DOUGH_MODE")
    if bread == "3":
        tokens.append("BREAD_DOUGH_MODE_2")
    # Full proto first (UNOWN_A, BURMY_PLANT) — matches PokeMiners pm*.fPROTO.icon.png
    tokens.extend(_master_form_protos(dex, form_id))
    ft = form_token(dex, form_id)
    if ft:
        tokens.append(ft)
        tokens.extend(_FORM_ALIASES.get(ft, []))
    # unique, keep order
    seen = set()
    out = []
    for tok in tokens:
        if tok and tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def _lookup(name):
    return ADDR_BY_NAME.get(name) or ADDR_BY_NAME.get(name.lower())


def resolve_pokemon(filename: str) -> tuple[Path | None, str]:
    m = UICONS_POKE.match(filename)
    if not m:
        return None, "unparsed"
    dex, b, e, f, c, g, a, s = m.groups()
    shiny = bool(s)
    gender = g if g and g not in ("0", "1") else None
    wants_costume = bool(c)
    wants_form = bool(f) and bool(_master_form_protos(dex, f) or form_token(dex, f))
    wants_evo = bool(e)
    # Gigantamax (_b2, Urshifu _b3): dedicated fGIGANTAMAX Addressable art must
    # not be preempted by the numbered base shortcut. Dynamax (_b1) has no art
    # of its own by design and keeps resolving to base.
    wants_giga = b in ("2", "3")
    wants_shiny = shiny
    forms = _form_tokens(dex, f, b, e)
    costumes = []
    if c:
        mapped = COSTUME_BY_ID.get(int(c))
        if mapped:
            costumes.append(mapped)

    def try_addr(form, costume, gen, sh, tag):
        key = addr_key(dex, form, costume, gen, sh)
        # Native 256 Addressable (same pm*.icon.png names, inside Pokemon - 256x256/)
        p = PX256_BY_NAME.get(key) or PX256_BY_NAME.get(key.lower())
        if p:
            return p, "256-addr"
        p = _lookup(key)
        return (p, tag) if p else None

    # Quality first: native Pokemon-256x256 before Addressable (never upscale ~100px crops).
    form_opts = list(forms) if forms else []
    # Costumes/base art live on pm{dex}.icon.png (form=None). Don't require a form token
    # unless the UIcons name actually asked for _f.
    if not wants_form:
        form_opts.append(None)
    if not form_opts:
        form_opts = [None]
    if wants_costume:
        costume_opts = costumes  # only proto-mapped names; never guess every costume
    else:
        costume_opts = [None]

    d3 = f"{int(dex):03d}"
    form_idx = "00"
    if e:
        # Numbered mega slots: _51 first mega, _52 second. Proto ids (see
        # evo_form): e1 plain Mega / legacy X, e2 Mega X, e3 Mega Y, e4 Primal
        # (Addressable only, no numbered slot). Dual-mega species are the ones
        # with a _52 file.
        dual = f"pokemon_icon_{int(dex):03d}_52.png" in PX256_BY_NAME
        if e == "1":
            form_idx = "51"
        elif e == "2":
            form_idx = "51" if dual else "52"
        elif e == "3":
            form_idx = "52"
        else:
            form_idx = None
    elif gender == "2" and not f:
        form_idx = "01"
    costume_idx = f"{int(c):02d}" if c else None
    shiny_s = "_shiny" if shiny else ""
    names_256 = []
    if costume_idx:
        names_256.append(f"pokemon_icon_{d3}_{form_idx}_{costume_idx}{shiny_s}.png")
        names_256.append(f"pokemon_icon_{d3}_00_{costume_idx}{shiny_s}.png")
        if shiny:
            names_256.append(f"pokemon_icon_{d3}_{form_idx}_{costume_idx}.png")
            names_256.append(f"pokemon_icon_{d3}_00_{costume_idx}.png")
    if e:
        names_256.append(f"pokemon_icon_{d3}_{form_idx}{shiny_s}.png")
        names_256.append(f"pokemon_icon_{d3}_{form_idx}.png")
    if not wants_costume and not wants_form and not wants_giga and not wants_evo:
        # Only when no specific form / Gigantamax was requested. A form request
        # must never shortcut to the numbered base file here: species with both
        # a numbered base and Addressable form art (Spinda patterns, GMAX)
        # would silently get base art. Form-specific Addressable candidates are
        # tried next; a form with no art of its own falls through to the miss.
        names_256.append(f"pokemon_icon_{d3}_{form_idx}{shiny_s}.png")
        if gender != "2":
            # Same trap for female variants: the numbered base must not
            # preempt Addressable .g2 art (female Eevee). The _01 female slot
            # above still wins when it exists; otherwise the Addressable loop
            # runs, and step 5 returns base art for non-dimorphic species.
            names_256.append(f"pokemon_icon_{d3}_00{shiny_s}.png")
    for name in names_256:
        p = PX256_BY_NAME.get(name) or PX256_BY_NAME.get(name.lower())
        if p:
            if wants_costume and costume_idx and f"_{costume_idx}" not in name.replace(d3, ""):
                continue
            if wants_evo and form_idx in ("51", "52") and f"_{form_idx}" not in name:
                continue
            return p, "256"

    # Female without a numbered _01 slot: dedicated Addressable .g2 art beats
    # the numbered base (female Eevee), but the numbered base still beats the
    # Addressable base for non-dimorphic species (numbered-first policy).
    if gender == "2" and not wants_form and not wants_costume and not wants_evo:
        for sh in ([True] if shiny else [False]):
            hit = try_addr(None, None, "2", sh, "addr")
            if hit:
                return hit
        p = PX256_BY_NAME.get(f"pokemon_icon_{d3}_00{shiny_s}.png")
        if p:
            return p, "256"

    # Addressable only when no native 256 match (forms/costumes missing from 256 folder)
    for costume in costume_opts or []:
        for form in form_opts:
            for sh in ([True] if shiny else [False]):
                hit = try_addr(form, costume, gender, sh, "addr")
                if hit:
                    return hit
                if gender:
                    hit = try_addr(form, costume, None, sh, "addr-nogender")
                    if hit:
                        return hit

    # 3. Unique addressable costume for this dex if costume still unmatched
    if wants_costume:
        uniq = _addr_costumes_by_dex().get(dex, set())
        if len(uniq) == 1:
            only = next(iter(uniq))
            for form in form_opts:
                hit = try_addr(form, only, gender, shiny, "addr-unique-costume")
                if hit:
                    return hit
                hit = try_addr(form, only, None, shiny, "addr-unique-costume")
                if hit:
                    return hit
                if not shiny:
                    hit = try_addr(form, only, None, False, "addr-unique-costume")
                    if hit:
                        return hit

    # 4. If a form/evo/costume/shiny was requested and we still have no match,
    #    do NOT silently use the default species. Caller falls back to wwm.
    if wants_costume or wants_evo or wants_form or wants_shiny:
        # last-ditch: non-shiny miners for a shiny request of the SAME variant
        if wants_shiny and not wants_costume:
            for form in form_opts:
                hit = try_addr(form, None, gender, False, "addr-noshiny")
                if hit:
                    return hit
                hit = try_addr(form, None, None, False, "addr-noshiny")
                if hit:
                    return hit
        if wants_costume or wants_evo or wants_form:
            return None, "miss"

    # 5. Default species (plain / shadow / dmax-without-gmax-art)
    for sh in ([True, False] if shiny else [False]):
        hit = try_addr(None, None, gender, sh, "addr-base-shiny" if sh else "addr-base")
        if hit:
            return hit
        hit = try_addr(None, None, None, sh, "addr-base")
        if hit:
            return hit
    for form in form_opts:
        hit = try_addr(form, None, None, False, "addr-default-form")
        if hit:
            return hit
    p = PX256_BY_NAME.get(f"pokemon_icon_{d3}_00.png")
    if p:
        return p, "256"
    return None, "miss"


def resolve_type(filename: str) -> tuple[Path | None, str]:
    m = re.match(r"^(\d+)\.png$", filename)
    if not m:
        return None, "miss"
    n = int(m.group(1))
    # UIcons 0=None, 1=Normal...18=Fairy. Miners ico_0_normal is type 1.
    if n == 0:
        return None, "miss-none"
    idx = n - 1
    for p in (MINERS / "Types").glob(f"ico_{idx}_*.png"):
        if "bordered" not in p.name.lower():
            return p, "types-ico"
    bordered = list((MINERS / "Types").glob(f"POKEMON_TYPE_*.png"))
    type_ids = MASTER.get("type_ids") or {}
    name = (type_ids.get(str(n)) or "").upper()
    for p in bordered:
        if name and name in p.name.upper() and "BORDERED" not in p.name.upper():
            return p, "types-named"
    return None, "miss"


WEATHER_MAP = {
    "1.png": "weatherIcon_large_clearDay.png",
    "1_d.png": "weatherIcon_large_clearDay.png",
    "1_n.png": "weatherIcon_large_clearNight.png",
    "2.png": "weatherIcon_large_rainDay.png",
    "2_d.png": "weatherIcon_large_rainDay.png",
    "2_n.png": "weatherIcon_large_rainNight.png",
    "3.png": "weatherIcon_large_partlyCloudyDay.png",
    "3_d.png": "weatherIcon_large_partlyCloudyDay.png",
    "3_n.png": "weatherIcon_large_partlyCloudyNight.png",
    "4.png": "weatherIcon_large_overcastDay.png",
    "4_d.png": "weatherIcon_large_overcastDay.png",
    "4_n.png": "weatherIcon_large_overcastNight.png",
    "5.png": "weatherIcon_large_windyDay.png",
    "5_d.png": "weatherIcon_large_windyDay.png",
    "5_n.png": "weatherIcon_large_windyNight.png",
    "6.png": "weatherIcon_large_snowDay.png",
    "6_d.png": "weatherIcon_large_snowDay.png",
    "6_n.png": "weatherIcon_large_snowNight.png",
    "7.png": "weatherIcon_large_fogDay.png",
    "7_d.png": "weatherIcon_large_fogDay.png",
    "7_n.png": "weatherIcon_large_fogNight.png",
}


def resolve_weather(filename: str) -> tuple[Path | None, str]:
    name = WEATHER_MAP.get(filename)
    if not name:
        return None, "miss"
    p = (MINERS / "Weather") / name
    return (p, "weather") if p.exists() else (None, "miss")


def resolve_item(filename: str) -> tuple[Path | None, str]:
    m = re.match(r"^(\d+)(?:_a(\d+))?\.png$", filename)
    if not m:
        return None, "miss"
    iid = int(m.group(1))
    amt = m.group(2)
    names = [
        f"Item_{iid:04d}.png",
        f"Item_{iid:04d}_{amt}.png" if amt else None,
        f"Item_{iid:03d}.png",
        f"Item_{iid}.png",
    ]
    if iid == 1:
        names.append("pokeball_sprite.png")
    proto = ((MASTER.get("items") or {}).get(str(iid)) or {}).get("proto") or ""
    if proto:
        names.append(proto.replace("ITEM_", "") + ".png")
        names.append(proto + ".png")
    for n in names:
        if not n:
            continue
        p = ITEMS_BY_NAME.get(n) or ITEMS_BY_NAME.get(n.lower())
        if p:
            return p, "item"
    return None, "miss"


TEAM_MAP = {
    "0.png": ["TeamLess.png", "teamless.png", "profile_teamless.png"],
    "1.png": ["team_blue.png", "profile_blue.png"],
    "2.png": ["team_red.png", "profile_red.png"],
    "3.png": ["team_yellow.png", "profile_yellow.png"],
}

RAID_EGG = {
    "1.png": "ic_raid_egg_normal.png",
    "1_h.png": "ic_raid_egg_normal.png",
    "2.png": "ic_raid_egg_normal.png",
    "2_h.png": "ic_raid_egg_normal.png",
    "3.png": "ic_raid_egg_rare.png",
    "3_h.png": "ic_raid_egg_rare.png",
    "4.png": "ic_raid_egg_rare.png",
    "4_h.png": "ic_raid_egg_rare.png",
    "5.png": "ic_raid_egg_legendary.png",
    "5_h.png": "ic_raid_egg_legendary.png",
    "6.png": "ic_raid_egg_legendary.png",
    "6_h.png": "ic_raid_egg_legendary.png",
}


def resolve_generic(rel: Path) -> tuple[Path | None, str]:
    folder = rel.parts[0]
    name = rel.name
    if folder == "pokemon":
        return resolve_pokemon(name)
    if folder == "type" or folder == "nest":
        # nest pins are type-colored; try type icons from miners
        return resolve_type(name)
    if folder == "weather":
        return resolve_weather(name)
    if folder == "team":
        for cand in TEAM_MAP.get(name, []):
            p = ALL_MINERS.get(cand) or ALL_MINERS.get(cand.lower())
            if p:
                return p, "team"
        return None, "miss"
    if folder == "raid":
        egg = RAID_EGG.get(name)
        if egg:
            p = (MINERS / "Raids") / egg
            if p.exists():
                return p, "raid-egg"
        return None, "miss"
    if folder == "reward" and len(rel.parts) >= 3 and rel.parts[1] == "item":
        return resolve_item(name)
    if folder == "tappable":
        # maple_tappable_icon.png etc
        stem = name.replace(".png", "").replace("TAPPABLE_TYPE_", "").lower()
        for cand in (
            f"{stem}_tappable_icon.png",
            f"maple_tappable_icon.png" if "maple" in stem else None,
            f"{stem}.png",
        ):
            if not cand:
                continue
            p = ALL_MINERS.get(cand) or ALL_MINERS.get(cand.lower())
            if p:
                return p, "tappable"
        return None, "miss"
    if folder == "invasion":
        p = ALL_MINERS.get("ic_rocket_map_pin.v4.png") or ALL_MINERS.get("teamrocket_r.png")
        # only use generic rocket pin for unknown invasions? Too lossy. miss unless exact.
        return None, "miss"
    return None, "miss"


def enhance_rgba(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    rgb = im.convert("RGB")
    rgb = ImageEnhance.Color(rgb).enhance(SATURATION)
    rgb = ImageEnhance.Contrast(rgb).enhance(CONTRAST)
    rgb = ImageEnhance.Brightness(rgb).enhance(BRIGHTNESS)
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def add_inset_stroke(im: Image.Image, stroke: int = STROKE) -> Image.Image:
    im = im.convert("RGBA")
    w, h = im.size
    if min(w, h) <= stroke * 2 + 2:
        return im
    scale = min((w - stroke * 2) / w, (h - stroke * 2) / h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    small = im.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(small, ((w - nw) // 2, (h - nh) // 2), small)
    alpha = canvas.getchannel("A")
    dilated = alpha
    for _ in range(stroke):
        dilated = dilated.filter(ImageFilter.MaxFilter(3))
    dilated = dilated.filter(ImageFilter.GaussianBlur(0.45))
    stroke_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    stroke_layer.putalpha(dilated)
    return Image.alpha_composite(stroke_layer, canvas)


def fit_to(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    im = im.convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
    tw, th = size
    scale = min(tw / max(im.width, 1), th / max(im.height, 1))
    # leave a little room if we will stroke; caller handles stroke inset
    nw = max(1, int(round(im.width * scale)))
    nh = max(1, int(round(im.height * scale)))
    small = im.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.paste(small, ((tw - nw) // 2, (th - nh) // 2), small)
    return canvas


def process_one(rel_s: str) -> tuple[str, str, str]:
    rel = Path(rel_s)
    wwm = WWM / rel
    dest = OUT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    target_size = Image.open(wwm).size
    src, tag = resolve_generic(rel)
    folder = rel.parts[0]
    if src is None:
        src = wwm
        tag = "wwm-fallback"
    im = Image.open(src).convert("RGBA")
    if src != wwm:
        im = fit_to(im, target_size)
    else:
        im = im.resize(target_size, Image.Resampling.LANCZOS) if im.size != target_size else im
    if folder not in SKIP_OUTLINE:
        extrema = im.getchannel("A").getextrema()
        if extrema[0] < 250:
            im = enhance_rgba(im)
            im = add_inset_stroke(im, STROKE)
        else:
            im = enhance_rgba(im)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "PNG", optimize=True)
    return rel_s, tag, f"{src}"


def main():
    load_indexes()
    print("addr", len(ADDR_BY_NAME), "256", len(PX256_BY_NAME), "items", len(ITEMS_BY_NAME), "all", len(ALL_MINERS), flush=True)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for p in WWM.rglob("*"):
        if p.is_dir() or p.suffix.lower() == ".png":
            continue
        dest = OUT / p.relative_to(WWM)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
    pngs = [str(p.relative_to(WWM)) for p in WWM.rglob("*.png")]
    print("processing", len(pngs), flush=True)
    counts = Counter()
    t0 = time.time()
    workers = 8
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(process_one, rel): rel for rel in pngs}
        done = 0
        for fut in as_completed(futs):
            rel, tag, _src = fut.result()
            counts[tag.split("-")[0] if tag.startswith("addr") else tag] += 1
            # keep addr* together-ish
            if tag.startswith("addr"):
                counts["addr"] += 1
            done += 1
            if done % 1000 == 0 or done == len(pngs):
                print(f"{done}/{len(pngs)} {dict(counts)} {time.time()-t0:.1f}s", flush=True)
    print("DONE", dict(counts), flush=True)
    REPO_ROOT / "bigfun-coverage.json".write_text(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
