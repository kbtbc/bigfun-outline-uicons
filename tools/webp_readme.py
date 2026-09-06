#!/usr/bin/env python3
"""Rewrite README.md raw-URL block for the webp branch.

Used by .github/workflows/sync-webp.yml when rebuilding the webp branch from
main. Fails loudly if main's README block changed, so the sync workflow
surfaces the drift instead of silently shipping a wrong README.
"""
from pathlib import Path

OLD = """Raw URL:
https://raw.githubusercontent.com/kbtbc/bigfun-outline-uicons/main/

WebP variant (lossless, ~30% smaller, same icons) on the [`webp`](https://github.com/kbtbc/bigfun-outline-uicons/tree/webp) branch:
https://raw.githubusercontent.com/kbtbc/bigfun-outline-uicons/webp/"""

NEW = """**This is the lossless WebP branch**: pixel-identical to `main`, ~30% smaller downloads. Raw URL:
https://raw.githubusercontent.com/kbtbc/bigfun-outline-uicons/webp/

PNG original on [`main`](https://github.com/kbtbc/bigfun-outline-uicons):
https://raw.githubusercontent.com/kbtbc/bigfun-outline-uicons/main/"""


def main() -> int:
    p = Path(__file__).resolve().parent.parent / "README.md"
    t = p.read_text(encoding="utf-8")
    if NEW in t:
        print("README already in webp form")
        return 0
    if OLD not in t:
        print("README raw-URL block changed on main; update tools/webp_readme.py")
        return 1
    p.write_text(t.replace(OLD, NEW), encoding="utf-8")
    print("README pointed at webp branch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
