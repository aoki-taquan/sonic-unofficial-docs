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
  - さらにそのセクション本文が **3 行以上の非空行** と
    **1 個以上のコードブロック (``` フェンス)** を含むこと (内容充実度)

Usage:
    python3 meta/scripts/check_troubleshoot_section.py            # 一覧
    python3 meta/scripts/check_troubleshoot_section.py --check    # CI gate
    python3 meta/scripts/check_troubleshoot_section.py --thin     # 内容不足のみ
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

MIN_SECTION_NONEMPTY_LINES = 3
MIN_SECTION_CODEBLOCKS = 1


def extract_section_body(text: str, header_match: re.Match[str]) -> str:
    """Return the body text from after the matched H2 to the next H2 (or EOF)."""
    start = header_match.end()
    # Find next H2 boundary
    next_h2 = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_h2.start() if next_h2 else len(text)
    return text[start:end]


def section_is_thin(body: str) -> bool:
    nonempty = [ln for ln in body.splitlines() if ln.strip()]
    fences = len(re.findall(r"^```", body, re.MULTILINE))
    codeblocks = fences // 2
    if len(nonempty) < MIN_SECTION_NONEMPTY_LINES:
        return True
    if codeblocks < MIN_SECTION_CODEBLOCKS:
        return True
    return False


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


def check(pages: list[Path]) -> tuple[list[Path], list[Path]]:
    """Return (missing_section_pages, thin_section_pages)."""
    missing: list[Path] = []
    thin: list[Path] = []
    for f in pages:
        text = f.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) < MIN_LINES:
            continue
        ver = parse_frontmatter_verification(text)
        if ver not in TARGET_VERIFICATION:
            continue
        m = TROUBLESHOOT_H2_RE.search(text)
        if not m:
            missing.append(f)
            continue
        body = extract_section_body(text, m)
        if section_is_thin(body):
            thin.append(f)
    return missing, thin


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit code 1 if any missing or thin pages exist",
    )
    parser.add_argument(
        "--thin",
        action="store_true",
        help="print only thin-content pages",
    )
    args = parser.parse_args()

    pages = collect_target_pages()
    missing, thin = check(pages)

    if args.thin:
        if not thin:
            print("OK: no thin troubleshoot sections")
            return 0
        print(f"THIN troubleshoot/verify-command section ({len(thin)} page(s)):")
        for f in thin:
            print(f"  {f.relative_to(REPO_ROOT)}")
        return 1 if args.check else 0

    if not missing and not thin:
        print(
            f"OK: all {len(pages)} candidate pages have a sufficient troubleshoot/verify-command section"
        )
        return 0

    if missing:
        print(f"MISSING troubleshoot/verify-command section ({len(missing)} page(s)):")
        for f in missing:
            print(f"  {f.relative_to(REPO_ROOT)}")
    if thin:
        print(f"THIN troubleshoot/verify-command section ({len(thin)} page(s)):")
        for f in thin:
            print(f"  {f.relative_to(REPO_ROOT)}")

    if args.check:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
