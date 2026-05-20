#!/usr/bin/env python3
"""Apply meta/hld-yang-map.json to populate empty `related.yang` lists.

For each entry in the map:
- Locate docs/<path>.
- Parse frontmatter; if `_no_yang` or `_no_related` is true, skip.
- If `related.yang` is already non-empty, skip.
- Validate every module name exists in meta/index/yang.json.
- Write the list back, preserving everything else.

Usage: meta/scripts/apply_hld_yang_map.py [--dry-run]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
MAP_FILE = ROOT / "meta" / "hld-yang-map.json"
YANG_INDEX = ROOT / "meta" / "index" / "yang.json"


def split_fm(text: str):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    fm = text[4:end]
    body = text[end + 5 :]
    return fm, body


def main() -> int:
    dry = "--dry-run" in sys.argv
    mapping = json.loads(MAP_FILE.read_text())
    mapping = {k: v for k, v in mapping.items() if not k.startswith("_")}

    yang_modules = {d["module"] for d in json.loads(YANG_INDEX.read_text())}

    updated = 0
    skipped: list[str] = []
    for rel_path, modules in mapping.items():
        path = DOCS / rel_path
        if not path.exists():
            skipped.append(f"missing: {rel_path}")
            continue
        bad = [m for m in modules if m not in yang_modules]
        if bad:
            skipped.append(f"bad-module {rel_path}: {bad}")
            continue
        text = path.read_text()
        fm_text, body = split_fm(text)
        if fm_text is None:
            skipped.append(f"no-frontmatter: {rel_path}")
            continue
        fm = yaml.safe_load(fm_text) or {}
        if fm.get("_no_yang") or fm.get("_no_related"):
            skipped.append(f"opt-out: {rel_path}")
            continue
        related = fm.get("related") or {}
        if not isinstance(related, dict):
            skipped.append(f"odd-related: {rel_path}")
            continue
        cur = related.get("yang") or []
        if cur:
            skipped.append(f"already-has-yang: {rel_path}")
            continue
        related["yang"] = list(modules)
        # Preserve key order: ensure cli, config_db, yang are present
        for k in ("config_db", "cli", "yang"):
            related.setdefault(k, [])
        fm["related"] = related
        new_fm = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=1000)
        new_text = f"---\n{new_fm}---\n{body}"
        if dry:
            print(f"WOULD UPDATE {rel_path}: yang={modules}")
        else:
            path.write_text(new_text)
            print(f"UPDATED {rel_path}: yang={modules}")
        updated += 1

    print(f"\n== summary: updated={updated}, skipped={len(skipped)} ==")
    for s in skipped:
        print(f"  SKIP {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
