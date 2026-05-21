#!/usr/bin/env python3
"""Check awesome-pages `.pages` files against the actual filesystem.

For each directory under `docs/` that contains a `.pages` file:

1. Every entry listed under `nav:` must exist (as `.md` file or sub-directory
   that itself contains content).
2. Every `.md` file in the directory must be listed in `nav:` unless the
   `.pages` uses the awesome-pages `...` wildcard (rest auto-included).
3. No entry may appear more than once in `nav:`.

Exceptions can be allowed via `meta/pages-integrity-exceptions.json` with the
following shape:

  {
    "missing": ["docs/foo/.pages::bar.md"],
    "orphans": ["docs/foo/baz.md"],
    "duplicates": ["docs/foo/.pages::qux.md"]
  }

Usage:
  python meta/scripts/check_pages_integrity.py            # human report
  python meta/scripts/check_pages_integrity.py --check    # CI mode, exit 1 on issues
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
EXCEPTIONS_PATH = REPO_ROOT / "meta" / "pages-integrity-exceptions.json"


def load_exceptions() -> dict:
    if not EXCEPTIONS_PATH.exists():
        return {"missing": [], "orphans": [], "duplicates": []}
    with EXCEPTIONS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return {
        "missing": set(data.get("missing", [])),
        "orphans": set(data.get("orphans", [])),
        "duplicates": set(data.get("duplicates", [])),
    }


def parse_pages(pages_path: Path) -> tuple[list[str], bool]:
    """Return (nav_entries, has_wildcard)."""
    with pages_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    nav = data.get("nav") or []
    entries: list[str] = []
    wildcard = False

    def walk(items: list) -> None:
        nonlocal wildcard
        for item in items:
            if isinstance(item, dict):
                # awesome-pages allows `- Title: path.md` or `- Title: [list...]`
                for _, v in item.items():
                    if isinstance(v, str):
                        if v.strip() == "...":
                            wildcard = True
                        else:
                            entries.append(v.strip())
                    elif isinstance(v, list):
                        walk(v)
            elif isinstance(item, str):
                if item.strip() == "...":
                    wildcard = True
                else:
                    entries.append(item.strip())

    walk(nav)
    return entries, wildcard


def check() -> tuple[list[str], list[str], list[str]]:
    exceptions = load_exceptions()
    missing: list[str] = []
    orphans: list[str] = []
    duplicates: list[str] = []

    for pages_path in sorted(DOCS_DIR.rglob(".pages")):
        directory = pages_path.parent
        rel_pages = pages_path.relative_to(REPO_ROOT).as_posix()

        try:
            entries, wildcard = parse_pages(pages_path)
        except yaml.YAMLError as e:
            missing.append(f"{rel_pages}::<parse error: {e}>")
            continue

        # 1. Missing entries
        seen: dict[str, int] = {}
        for entry in entries:
            seen[entry] = seen.get(entry, 0) + 1
            target = directory / entry
            if not target.exists():
                key = f"{rel_pages}::{entry}"
                if key not in exceptions["missing"]:
                    missing.append(key)

        # 3. Duplicates
        for entry, count in seen.items():
            if count > 1:
                key = f"{rel_pages}::{entry}"
                if key not in exceptions["duplicates"]:
                    duplicates.append(key)

        # 2. Orphans: only if no wildcard
        if not wildcard:
            listed = set(entries)
            for md_file in sorted(directory.glob("*.md")):
                rel = md_file.name
                if rel in listed:
                    continue
                rel_md = md_file.relative_to(REPO_ROOT).as_posix()
                if rel_md in exceptions["orphans"]:
                    continue
                orphans.append(rel_md)

    return missing, orphans, duplicates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI mode: print counts to stderr and exit 1 on any issue.",
    )
    args = parser.parse_args()

    missing, orphans, duplicates = check()
    total = len(missing) + len(orphans) + len(duplicates)

    if args.check:
        sys.stderr.write(
            f"pages-integrity: missing={len(missing)} orphans={len(orphans)} "
            f"duplicates={len(duplicates)} total={total}\n"
        )
        if total:
            sys.stderr.write("--- missing entries (listed in .pages but file/dir absent) ---\n")
            for m in missing:
                sys.stderr.write(f"  {m}\n")
            sys.stderr.write("--- orphan .md files (present but not listed) ---\n")
            for o in orphans:
                sys.stderr.write(f"  {o}\n")
            sys.stderr.write("--- duplicate entries ---\n")
            for d in duplicates:
                sys.stderr.write(f"  {d}\n")
            return 1
        return 0

    print(f"missing:    {len(missing)}")
    for m in missing:
        print(f"  - {m}")
    print(f"orphans:    {len(orphans)}")
    for o in orphans:
        print(f"  - {o}")
    print(f"duplicates: {len(duplicates)}")
    for d in duplicates:
        print(f"  - {d}")
    print(f"total:      {total}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
