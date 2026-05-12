#!/usr/bin/env python3
"""Find pages where frontmatter `related.{cli,config_db,yang}` has 1 or 2
empty lists (i.e. partially populated). Fully-empty pages and fully-populated
pages are excluded. `_no_related: true` opt-outs are also excluded.

Usage:
    meta/scripts/find_partial_empty_related.py [--root docs] [--targets DIR[,DIR]]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

DEFAULT_TARGET_DIRS = [
    "docs/reference/runbooks",
    "docs/management",
    "docs/architecture",
    "docs/overlay",
    "docs/routing",
    "docs/switching",
    "docs/internals",
    "docs/topics",
    "docs/system",
    "docs/platform",
    "docs/acl-qos",
    "docs/guides",
]

FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def split_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--targets", default=",".join(DEFAULT_TARGET_DIRS))
    args = ap.parse_args()

    root = Path(args.root).resolve()
    dirs = [d.strip() for d in args.targets.split(",") if d.strip()]
    partial: list[tuple[Path, list[str], list[str]]] = []
    for d in dirs:
        full = root / d
        if not full.is_dir():
            continue
        for p in sorted(full.rglob("*.md")):
            if p.name == "index.md":
                continue
            try:
                fm = split_frontmatter(p.read_text(encoding="utf-8"))
            except OSError:
                continue
            if not fm:
                continue
            # Top-level _no_related is a legacy fallback; the canonical
            # location is under `related:` (see SCHEMA.md "related の opt-out
            # マーカー").
            if fm.get("_no_related") is True:
                continue
            rel = fm.get("related") or {}
            if not isinstance(rel, dict):
                continue
            # Full opt-out: skip entirely.
            if rel.get("_no_related") is True:
                continue
            # Narrower opt-outs: a given axis is considered "allowed empty"
            # and is not reported as a partial-empty axis.
            opt_axes = set()
            if rel.get("_no_related_yang") is True or rel.get("_no_yang") is True:
                opt_axes.add("yang")
            if rel.get("_no_related_cli") is True:
                opt_axes.add("cli")
            if rel.get("_no_related_config_db") is True:
                opt_axes.add("config_db")
            empties = []
            haves = []
            for k in ("cli", "config_db", "yang"):
                v = rel.get(k) or []
                if isinstance(v, list) and v:
                    haves.append(k)
                elif k in opt_axes:
                    # opted-out axis: not counted as empty
                    continue
                else:
                    empties.append(k)
            if empties and haves:
                partial.append((p.relative_to(root), empties, haves))
    for p, empties, haves in partial:
        print(f"{p}\tempty={','.join(empties)}\thave={','.join(haves)}")
    print(f"\nTotal partial-empty pages: {len(partial)}", file=sys.stderr)


if __name__ == "__main__":
    main()
