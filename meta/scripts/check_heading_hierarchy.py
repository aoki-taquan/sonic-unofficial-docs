#!/usr/bin/env python3
"""Lint docs/ for heading hierarchy skips (a11y).

Walks ``docs/**/*.md`` and flags any heading whose level jumps by more than
one relative to the previously seen heading (e.g. ``##`` followed by ``####``,
or ``#`` followed by ``###``).

Skip rules:

* Frontmatter (``---`` block at top of file) is ignored.
* Fenced code blocks (``` and ~~~) are ignored — ``#`` lines inside are not
  headings.
* Setext-style headings are not considered (the repo uses ATX style).

Usage:
    python meta/scripts/check_heading_hierarchy.py            # human report
    python meta/scripts/check_heading_hierarchy.py --check    # CI informational

Exit codes:
    0  always (informational mode)
    1  in default mode if violations exist (so contributors notice locally)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
FENCE_RE = re.compile(r"^(```|~~~)")


def extract_headings(text: str) -> list[tuple[int, int, str]]:
    """Return list of (line_no, level, line_text) ATX headings."""
    lines = text.splitlines()
    out: list[tuple[int, int, str]] = []
    in_fence = False
    fence_marker = ""
    # Frontmatter only at very top.
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines):
            if lines[i].strip() == "---":
                i += 1
                break
            i += 1
    for idx in range(i, len(lines)):
        line = lines[idx]
        m_fence = FENCE_RE.match(line)
        if m_fence:
            marker = m_fence.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            out.append((idx + 1, level, line.rstrip()))
    return out


def find_violations(path: Path) -> list[tuple[int, int, int, str]]:
    """Return list of (line_no, prev_level, level, line) skip violations."""
    text = path.read_text(encoding="utf-8")
    headings = extract_headings(text)
    violations: list[tuple[int, int, int, str]] = []
    prev_level = 0
    for line_no, level, line in headings:
        # The first heading is allowed at any level (typically H1).
        if prev_level == 0:
            prev_level = level
            continue
        if level > prev_level + 1:
            violations.append((line_no, prev_level, level, line))
        prev_level = level
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="CI informational mode: always exit 0")
    parser.add_argument("--paths", nargs="*", default=None,
                        help="optional list of paths to scan")
    args = parser.parse_args()

    if args.paths:
        files = [Path(p) for p in args.paths]
    else:
        files = sorted(DOCS_DIR.rglob("*.md"))

    total_violations = 0
    file_count_with_violations = 0
    print("# Heading hierarchy lint (a11y)\n")
    for path in files:
        try:
            violations = find_violations(path)
        except Exception as exc:
            print(f"! could not parse {path}: {exc}", file=sys.stderr)
            continue
        if not violations:
            continue
        file_count_with_violations += 1
        total_violations += len(violations)
        rel = path.relative_to(REPO_ROOT)
        print(f"## {rel}")
        for line_no, prev, lvl, line in violations:
            print(f"- L{line_no}: H{prev} -> H{lvl}: `{line.strip()}`")
        print()

    print(f"Total: {total_violations} skip violations in "
          f"{file_count_with_violations} files")

    if args.check:
        return 0
    return 1 if total_violations else 0


if __name__ == "__main__":
    sys.exit(main())
