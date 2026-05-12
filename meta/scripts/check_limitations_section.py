#!/usr/bin/env python3
"""Lint: 主要 HLD ページに「制限事項」セクションがあるか確認する。

対象:
  - ``docs/<area>/*.md`` (area は HLD 系: acl-qos, architecture, management,
    overlay, platform, routing, switching, system)
  - 行数 100 行以上
  - frontmatter の ``verification`` が ``code-verified`` または
    ``discrepancy-found``

判定:
  - ``## 制限事項`` / ``## Limitations`` / ``## 制限`` / ``## 既知の制限``
    のいずれかの H2 が含まれていれば OK

Usage:
    python3 meta/scripts/check_limitations_section.py            # 一覧
    python3 meta/scripts/check_limitations_section.py --check    # CI gate
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
AREAS = (
    "acl-qos",
    "architecture",
    "management",
    "overlay",
    "platform",
    "routing",
    "switching",
    "system",
)
SKIP_FILES = {"index.md"}
MIN_LINES = 100
TARGET_VERIFICATION = {"code-verified", "discrepancy-found"}

LIMITATIONS_H2_RE = re.compile(
    r"^##\s+(制限事項|Limitations|制限|既知の制限)\s*$", re.MULTILINE
)
VERIFICATION_RE = re.compile(r"^verification:\s*(\S+)\s*$", re.MULTILINE)


def parse_frontmatter_verification(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm = text[3:end]
    m = VERIFICATION_RE.search(fm)
    if not m:
        return None
    return m.group(1).strip()


def collect_target_pages() -> list[Path]:
    pages: list[Path] = []
    for area in AREAS:
        d = DOCS / area
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            if f.name in SKIP_FILES:
                continue
            pages.append(f)
    return pages


def check(pages: list[Path]) -> list[Path]:
    missing: list[Path] = []
    for f in pages:
        text = f.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) < MIN_LINES:
            continue
        ver = parse_frontmatter_verification(text)
        if ver not in TARGET_VERIFICATION:
            continue
        if not LIMITATIONS_H2_RE.search(text):
            missing.append(f)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit code 1 if any missing pages exist",
    )
    args = parser.parse_args()

    pages = collect_target_pages()
    missing = check(pages)

    if not missing:
        print(f"OK: all {len(pages)} candidate pages have a limitations section")
        return 0

    print(f"MISSING limitations section ({len(missing)} page(s)):")
    for f in missing:
        rel = f.relative_to(REPO_ROOT)
        print(f"  {rel}")

    if args.check:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
