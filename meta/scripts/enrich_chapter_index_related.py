#!/usr/bin/env python3
"""
Enrich `related.{cli,config_db,yang}` of chapter-index pages by aggregating
the same fields from child pages under the same directory.

- Scans docs/topics/NN-slug/index.md (page_kind: chapter-index).
- Collects child *.md (excluding index.md) sibling pages.
- Counts frequencies of each related entry across children.
- Merges into chapter-index frontmatter without overwriting existing entries.
- Caps each list at 7 items total. Existing entries are preserved first; the
  most frequent new entries are appended until the cap is reached.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CAP = 7
FIELDS = ("cli", "config_db", "yang")


def split_frontmatter(text: str):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    fm = text[4:end]
    body = text[end + 5 :]
    return yaml.safe_load(fm), body


def dump_frontmatter(fm: dict) -> str:
    return yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=4096)


def get_related_lists(fm: dict) -> dict:
    rel = fm.get("related") or {}
    if not isinstance(rel, dict):
        return {}
    out = {}
    for f in FIELDS:
        v = rel.get(f) or []
        if isinstance(v, list):
            out[f] = [str(x) for x in v]
        else:
            out[f] = []
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Drift detection: exit 1 if any chapter-index would be updated. Does not write files.",
    )
    args = parser.parse_args()

    chapter_indexes = []
    for p in sorted(DOCS.rglob("index.md")):
        text = p.read_text(encoding="utf-8")
        fm, _ = split_frontmatter(text)
        if fm and fm.get("page_kind") == "chapter-index":
            chapter_indexes.append(p)

    print(f"Found {len(chapter_indexes)} chapter-index pages")

    updated = 0
    drift_paths: list[Path] = []
    for idx_path in chapter_indexes:
        chap_dir = idx_path.parent
        children = sorted(
            c
            for c in chap_dir.glob("*.md")
            if c.name != "index.md"
        )
        if not children:
            continue

        counters = {f: Counter() for f in FIELDS}
        for c in children:
            ctext = c.read_text(encoding="utf-8")
            cfm, _ = split_frontmatter(ctext)
            if not cfm:
                continue
            rel = get_related_lists(cfm)
            for f in FIELDS:
                for item in rel[f]:
                    counters[f][item] += 1

        text = idx_path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        if fm is None:
            continue

        existing_related = fm.get("related") or {}
        if not isinstance(existing_related, dict):
            existing_related = {}

        changed = False
        for f in FIELDS:
            cur = existing_related.get(f) or []
            if not isinstance(cur, list):
                cur = []
            cur = [str(x) for x in cur]
            cur_set = set(cur)
            # Candidates ordered by frequency desc, then name
            cands = [
                name
                for name, _ in sorted(
                    counters[f].items(), key=lambda kv: (-kv[1], kv[0])
                )
                if name not in cur_set
            ]
            room = CAP - len(cur)
            if room > 0 and cands:
                add = cands[:room]
                if add:
                    cur = cur + add
                    changed = True
            if cur:
                existing_related[f] = cur

        if changed:
            fm["related"] = existing_related
            new_text = "---\n" + dump_frontmatter(fm) + "---\n" + body
            if args.check:
                drift_paths.append(idx_path)
                print(f"  drift: {idx_path.relative_to(ROOT)}")
            else:
                idx_path.write_text(new_text, encoding="utf-8")
                updated += 1
                print(f"  updated: {idx_path.relative_to(ROOT)}")

    if args.check:
        if drift_paths:
            print(
                f"ERROR: {len(drift_paths)} chapter-index page(s) out of sync with child related.* aggregates.\n"
                "Run: python3 meta/scripts/enrich_chapter_index_related.py",
                file=sys.stderr,
            )
            return 1
        print("OK: all chapter-index related.* are up to date")
        return 0

    print(f"Updated {updated} chapter-index pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
