#!/usr/bin/env python3
"""Clean up noise / already-documented backlog entries.

Targets:
  - Slugs that are generic HLD h2 sections (introduction[-N], scope[-N],
    overview, summary, revision, references, feature-name[-N], hld-name,
    abstract, background, requirements, definitions, terminology, etc.).
  - Slugs whose docs/<area>/<slug>.md already exists in the repo.

Behaviour:
  - dry-run by default: prints the candidates.
  - --apply: moves matched JSON files to meta/backlog/_archived/<area>/<slug>.json
    so we keep an audit trail rather than deleting outright.

Usage:
  python3 meta/scripts/cleanup_backlog.py            # dry-run
  python3 meta/scripts/cleanup_backlog.py --apply    # archive
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# Resolve repo root from this script location:
#   meta/scripts/cleanup_backlog.py -> repo root is parents[2]
ROOT = Path(__file__).resolve().parents[2]
BACKLOG = ROOT / "meta" / "backlog"
ARCHIVE = BACKLOG / "_archived"
DOCS = ROOT / "docs"

# Noise slug regex (HLD H2-derived junk that is not a real per-feature page).
NOISE_RE = re.compile(
    r"^("
    r"introduction"
    r"|overview"
    r"|summary"
    r"|abstract"
    r"|background"
    r"|scope"
    r"|references"
    r"|appendix"
    r"|revision"
    r"|requirements"
    r"|definitions"
    r"|definitions-abbreviations"
    r"|abbreviations"
    r"|terminology"
    r"|table-of-contents"
    r"|toc"
    r"|conclusion"
    r"|feature-name"
    r"|hld-name"
    r")(-\d+)?$"
)


def iter_backlog_files() -> list[Path]:
    files: list[Path] = []
    for p in BACKLOG.rglob("*.json"):
        # Skip already-archived files.
        try:
            p.relative_to(ARCHIVE)
            continue
        except ValueError:
            pass
        files.append(p)
    return sorted(files)


def classify(path: Path) -> str | None:
    """Return reason string if entry should be archived, else None."""
    area = path.parent.name
    slug = path.stem
    if NOISE_RE.match(slug):
        return f"noise-slug ({slug})"
    doc = DOCS / area / f"{slug}.md"
    if doc.exists():
        return "doc-exists"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Move matched files to meta/backlog/_archived/.")
    args = ap.parse_args()

    files = iter_backlog_files()
    matches: list[tuple[Path, str]] = []
    for f in files:
        reason = classify(f)
        if reason:
            matches.append((f, reason))

    noise = sum(1 for _, r in matches if r.startswith("noise-slug"))
    exists = sum(1 for _, r in matches if r == "doc-exists")
    print(f"Scanned {len(files)} backlog entries.")
    print(f"Matched: {len(matches)} (noise-slug={noise}, doc-exists={exists}).")
    for f, reason in matches[:30]:
        print(f"  [{reason}] {f.relative_to(ROOT)}")
    if len(matches) > 30:
        print(f"  ... and {len(matches) - 30} more.")

    if not args.apply:
        print("\nDry-run only. Pass --apply to archive.")
        return 0

    moved = 0
    for f, _reason in matches:
        rel = f.relative_to(BACKLOG)
        dest = ARCHIVE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(dest))
        moved += 1
    print(f"\nArchived {moved} entries under {ARCHIVE.relative_to(ROOT)}/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
