#!/usr/bin/env python3
"""Lint: 主要 HLD ページに「トラブルシュート」または「確認コマンド」セクションがあるか確認する。

対象:
  - ``docs/<area>/*.md`` (area は HLD 系: acl-qos, architecture, management,
    overlay, platform, routing, switching, system)
  - 行数 100 行以上
  - frontmatter の ``verification`` が ``code-verified`` または
    ``discrepancy-found``

判定:
  - ``## トラブルシュート`` / ``## トラブルシューティング`` / ``## 確認コマンド``
    / ``## Troubleshooting`` / ``## 動作確認`` のいずれかの H2 があれば OK

Usage:
    python3 meta/scripts/check_troubleshoot_section.py            # 一覧
    python3 meta/scripts/check_troubleshoot_section.py --check    # CI gate
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

TROUBLESHOOT_H2_RE = re.compile(
    r"^##\s+(?:\d+\.\s*)?(トラブルシュート|トラブルシューティング|確認コマンド|Troubleshooting|動作確認)\s*$",
    re.MULTILINE,
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
        if not TROUBLESHOOT_H2_RE.search(text):
            missing.append(f)
    return missing


def find_section_body(text: str) -> str | None:
    """対象 H2 セクション本文 (次の H2/EOF まで) を返す。複数あれば結合。"""
    lines = text.splitlines()
    bodies: list[str] = []
    i = 0
    while i < len(lines):
        if TROUBLESHOOT_H2_RE.match(lines[i]):
            j = i + 1
            buf: list[str] = []
            while j < len(lines) and not lines[j].startswith("## "):
                buf.append(lines[j])
                j += 1
            bodies.append("\n".join(buf))
            i = j
        else:
            i += 1
    if not bodies:
        return None
    return "\n\n".join(bodies)


def is_thin(body: str) -> bool:
    """3 行未満の本文または code block なしを thin と判定。"""
    non_empty = [l for l in body.splitlines() if l.strip()]
    if len(non_empty) < 3:
        return True
    if "```" not in body:
        return True
    return False


def find_thin(pages: list[Path]) -> list[Path]:
    thin: list[Path] = []
    for f in pages:
        text = f.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) < MIN_LINES:
            continue
        ver = parse_frontmatter_verification(text)
        if ver not in TARGET_VERIFICATION:
            continue
        body = find_section_body(text)
        if body is None:
            continue
        if is_thin(body):
            thin.append(f)
    return thin


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit code 1 if any missing pages exist",
    )
    parser.add_argument(
        "--thin",
        action="store_true",
        help="list pages whose troubleshoot/verify section is too thin (<3 lines or no code block)",
    )
    args = parser.parse_args()

    pages = collect_target_pages()
    if args.thin:
        thin = find_thin(pages)
        if not thin:
            print("OK: no thin troubleshoot/verify-command sections")
            return 0
        print(f"THIN troubleshoot/verify-command section ({len(thin)} page(s)):")
        for f in thin:
            rel = f.relative_to(REPO_ROOT)
            print(f"  {rel}")
        return 0

    missing = check(pages)

    if not missing:
        print(
            f"OK: all {len(pages)} candidate pages have a troubleshoot/verify-command section"
        )
        return 0

    print(f"MISSING troubleshoot/verify-command section ({len(missing)} page(s)):")
    for f in missing:
        rel = f.relative_to(REPO_ROOT)
        print(f"  {rel}")

    if args.check:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
