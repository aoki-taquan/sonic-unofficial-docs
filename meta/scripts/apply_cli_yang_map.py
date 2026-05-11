#!/usr/bin/env python3
"""Apply meta/cli-yang-map.json to back-fill related.yang in
docs/reference/cli/*.md.

For each CLI page where related.yang is empty / missing, look up the slug
in cli-yang-map.json, validate each YANG module against
meta/index/yang.json (authoritative SONiC YANG inventory), and write the
filtered list back to frontmatter.

Existing non-empty related.yang values are never overwritten.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = ROOT / "docs" / "reference" / "cli"
MAP_FILE = ROOT / "meta" / "cli-yang-map.json"
YANG_INDEX = ROOT / "meta" / "index" / "yang.json"

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def load_yang_modules() -> set[str]:
    data = json.loads(YANG_INDEX.read_text())
    return {m["module"] for m in data}


def load_map() -> dict[str, list[str]]:
    raw = json.loads(MAP_FILE.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def patch_file(path: Path, yang_list: list[str]) -> bool:
    text = path.read_text()
    m = FM_RE.match(text)
    if not m:
        return False
    fm_text = m.group(1)
    fm = yaml.safe_load(fm_text) or {}
    rel = fm.get("related") or {}
    existing = rel.get("yang") or []
    if existing:
        return False
    if not yang_list:
        return False
    rel["yang"] = yang_list
    # Ensure other keys present
    rel.setdefault("cli", rel.get("cli") or [])
    rel.setdefault("config_db", rel.get("config_db") or [])
    fm["related"] = rel
    new_fm = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False).rstrip()
    new_text = f"---\n{new_fm}\n---\n" + text[m.end():]
    path.write_text(new_text)
    return True


def main() -> int:
    yang_modules = load_yang_modules()
    mapping = load_map()
    updated = 0
    skipped_existing = 0
    no_map = []
    for path in sorted(CLI_DIR.glob("*.md")):
        slug = path.stem
        candidates = mapping.get(slug, [])
        # Validate against authoritative index
        validated = [m for m in candidates if m in yang_modules]
        text = path.read_text()
        mt = FM_RE.match(text)
        if not mt:
            continue
        fm = yaml.safe_load(mt.group(1)) or {}
        rel = fm.get("related") or {}
        if rel.get("yang"):
            skipped_existing += 1
            continue
        if not validated:
            if slug not in mapping:
                no_map.append(slug)
            continue
        if patch_file(path, validated):
            updated += 1
            print(f"updated {slug}: {validated}")
    print(f"\nTotal updated: {updated}")
    print(f"Skipped (had existing yang): {skipped_existing}")
    if no_map:
        print(f"No mapping entry for: {no_map}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
