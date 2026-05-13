#!/usr/bin/env python3
"""Lint docs/ for images with empty alt text (a11y).

Detects inline images of the form ``![](url)`` (empty alt) which fail
WCAG 1.1.1 (Non-text Content). Decorative images should use reference-style
``![][ref]`` with a description supplied in the link reference, or be
explicitly marked as decorative via ``role="presentation"`` (not enforced
in plain Markdown — flag for manual fix).

The script also reports very short alt text (1 character or fewer) as
suspicious.

Frontmatter and fenced code blocks are skipped.

Usage:
    python meta/scripts/check_image_alt.py            # human report
    python meta/scripts/check_image_alt.py --check    # CI informational

Exit codes:
    0  always (informational mode)
    1  in default mode if violations exist
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

# ``![alt](url)`` inline image. Group(1) = alt, group(2) = url.
IMG_INLINE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]+)\)")
FENCE_RE = re.compile(r"^(```|~~~)")


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, url, kind) violations.

    kind ∈ {"empty-alt", "very-short-alt"}.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    violations: list[tuple[int, str, str]] = []

    in_fence = False
    fence_marker = ""
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
        for m in IMG_INLINE_RE.finditer(line):
            alt = m.group("alt").strip()
            url = m.group("url").strip()
            if alt == "":
                violations.append((idx + 1, url, "empty-alt"))
            elif len(alt) <= 1:
                violations.append((idx + 1, url, "very-short-alt"))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="CI informational mode: always exit 0")
    args = parser.parse_args()

    files = sorted(DOCS_DIR.rglob("*.md"))
    total = 0
    files_with = 0
    print("# Image alt-text lint (a11y)\n")
    for path in files:
        try:
            v = scan_file(path)
        except Exception as exc:
            print(f"! could not parse {path}: {exc}", file=sys.stderr)
            continue
        if not v:
            continue
        files_with += 1
        total += len(v)
        rel = path.relative_to(REPO_ROOT)
        print(f"## {rel}")
        for line_no, url, kind in v:
            print(f"- L{line_no} [{kind}]: `{url}`")
        print()

    print(f"Total: {total} alt-text issues across {files_with} files")
    if args.check:
        return 0
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
