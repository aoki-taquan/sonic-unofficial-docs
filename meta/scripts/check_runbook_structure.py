#!/usr/bin/env python3
"""Check that docs/reference/runbooks/*.md pages contain the 5 required sections.

Required H2 sections (順不同可、見出し本文中に部分一致):
  1. 症状
  2. 切り分け
  3. 確認
  4. 原因
  5. 関連

Usage:
    python3 meta/scripts/check_runbook_structure.py            # 一覧表示
    python3 meta/scripts/check_runbook_structure.py --check    # CI gate
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_DIR = REPO_ROOT / "docs" / "reference" / "runbooks"

REQUIRED = ["症状", "切り分け", "確認", "原因", "関連"]
SKIP_FILES = {"index.md"}


def collect_runbooks() -> list[Path]:
    if not RUNBOOK_DIR.exists():
        return []
    return sorted(p for p in RUNBOOK_DIR.glob("*.md") if p.name not in SKIP_FILES)


def find_missing(text: str) -> list[str]:
    # ## 以上のヘッダを抽出
    headers = re.findall(r"^#{2,3}\s+.*$", text, re.MULTILINE)
    joined = "\n".join(headers)
    return [k for k in REQUIRED if k not in joined]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    runbooks = collect_runbooks()
    bad: list[tuple[Path, list[str]]] = []

    for path in runbooks:
        missing = find_missing(path.read_text(encoding="utf-8"))
        if missing:
            bad.append((path, missing))

    rel = lambda p: p.relative_to(REPO_ROOT).as_posix()

    if bad:
        print(
            f"[check_runbook_structure] {len(bad)} runbook(s) missing required sections:",
            file=sys.stderr,
        )
        for path, missing in bad:
            print(f"  - {rel(path)}: missing {missing}", file=sys.stderr)
    else:
        print(f"[check_runbook_structure] OK: {len(runbooks)} runbook(s) complete.")
        return 0

    if args.check:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
