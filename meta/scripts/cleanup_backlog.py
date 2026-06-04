#!/usr/bin/env python3
"""Clean up noise / already-documented / subsumed backlog entries.

Targets:
  - Slugs that are generic HLD h2 sections (introduction[-N], scope[-N],
    overview, summary, revision, references, feature-name[-N], hld-name,
    abstract, background, requirements, definitions, terminology, etc.).
  - Slugs whose docs/<area>/<slug>.md already exists in the repo.
<<<<<<< HEAD
  - **Subsumed**: the backlog entry's `target_path` does not exist on disk,
    but the primary HLD source it references is already cited by one or more
    pages under docs/**/*.md (the HLD was absorbed into a different slug, a
    multi-slug split, or re-homed to a different area). These entries are
    phantom paths from the audit's perspective — the work is done, just not
    under the slug the backlog originally assumed.
=======
  - Slugs that were implemented as a split-page family — docs/<area>/<slug>-{concepts,internals,operations,limitations,design,dpu-scope-*}*.md.
    Without this rule, audits keep counting backlog entries like
    `smartswitch-high-availability-high-level-design` as un-ported even
    though the equivalent HLD has already been split into multiple slugs.
>>>>>>> origin/main

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
import json
import re
import shutil
import sys
from functools import lru_cache
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


<<<<<<< HEAD
@lru_cache(maxsize=1)
def _all_docs_text() -> str:
    """Concatenate all docs/**/*.md (text only) into one searchable blob."""
    chunks: list[str] = []
    for p in DOCS.rglob("*.md"):
        try:
            chunks.append(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(chunks)


def _primary_source_paths(path: Path) -> list[str]:
    """Extract primary_sources[*].path strings from a backlog JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    srcs = data.get("primary_sources") or []
    paths: list[str] = []
    if isinstance(srcs, list):
        for src in srcs:
            if isinstance(src, dict):
                p = src.get("path")
                if isinstance(p, str) and p.strip():
                    paths.append(p.strip())
    return paths


def _is_subsumed(path: Path) -> bool:
    """True if backlog target_path is missing but primary HLD is cited by docs."""
    srcs = _primary_source_paths(path)
    if not srcs:
        return False
    blob = _all_docs_text()
    # If any primary source path appears in any docs/**/*.md (typically inside
    # frontmatter sources[].path or evidence blocks), the HLD has been
    # documented — under whatever slug the writer chose.
    return any(src in blob for src in srcs)


def _target_path(path: Path) -> str | None:
    """Return the backlog entry's declared target_path (relative to repo)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        tp = data.get("target_path")
        if isinstance(tp, str) and tp.strip():
            return tp.strip()
    return None
=======
def _has_split_implementation(area: str, slug: str) -> list[Path]:
    """Return list of docs that look like a split-page family for this slug.

    A split family is the pattern we use when a single large HLD is broken
    into several derived pages (e.g. `<slug>-concepts.md`,
    `<slug>-internals.md`, `<slug>-operations.md`, `<slug>-limitations.md`,
    `<slug>-dpu-scope-*.md`). When any such derivative exists we treat the
    original backlog entry as already-implemented — otherwise audits keep
    scoring it as a 0-point ghost page.
    """
    area_dir = DOCS / area
    if not area_dir.is_dir():
        return []
    # Match <slug>-<something>.md but not unrelated slugs that share a
    # prefix accidentally — require the next char to be `-`.
    return sorted(p for p in area_dir.glob(f"{slug}-*.md"))
>>>>>>> origin/main


def classify(path: Path) -> str | None:
    """Return reason string if entry should be archived, else None."""
    area = path.parent.name
    slug = path.stem
    if NOISE_RE.match(slug):
        return f"noise-slug ({slug})"
    doc = DOCS / area / f"{slug}.md"
    if doc.exists():
        return "doc-exists"
<<<<<<< HEAD
    # target_path missing — check whether the HLD was absorbed elsewhere.
    if _is_subsumed(path):
        return "subsumed"
    # target_path declared but missing on disk and no evidence the HLD was
    # absorbed elsewhere. The project has been in maintenance phase since
    # 2026-05 with hld-only==0 across docs/; these are deferred / abandoned
    # backlog items that pollute audit input with "file does not exist"
    # phantom paths. Archive them so the audit pool stays grounded in reality.
    tp = _target_path(path)
    if tp and not (ROOT / tp).exists():
        return "phantom-target"
=======
    split = _has_split_implementation(area, slug)
    if split:
        sample = split[0].name
        extra = f" +{len(split) - 1}" if len(split) > 1 else ""
        return f"doc-exists-split ({sample}{extra})"
>>>>>>> origin/main
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
<<<<<<< HEAD
    subsumed = sum(1 for _, r in matches if r == "subsumed")
    phantom = sum(1 for _, r in matches if r == "phantom-target")
    print(f"Scanned {len(files)} backlog entries.")
    print(
        f"Matched: {len(matches)} "
        f"(noise-slug={noise}, doc-exists={exists}, "
        f"subsumed={subsumed}, phantom-target={phantom})."
=======
    split = sum(1 for _, r in matches if r.startswith("doc-exists-split"))
    print(f"Scanned {len(files)} backlog entries.")
    print(
        f"Matched: {len(matches)} (noise-slug={noise}, doc-exists={exists}, "
        f"doc-exists-split={split})."
>>>>>>> origin/main
    )
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
