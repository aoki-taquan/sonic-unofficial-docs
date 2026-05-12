#!/usr/bin/env python3
"""Check that ``docs/reference/runbooks/*.md`` pages have the required 5 sections.

Runbook ページは運用者が短時間で読み切れるよう、最低限の構造を揃えておく。
本 linter は以下 5 セクション (H2) の有無を検証する:

1. ``## 症状``
2. 切り分け節 — ``## 切り分け`` / ``## 切り分けフロー`` / ``## 切り分け手順`` のいずれか
3. 確認コマンド節 — ``## 確認コマンド`` / ``## コマンド`` / ``## 確認`` のいずれか、
   または切り分け節配下に ``bash`` 系コードブロックが 1 つ以上含まれていれば OK
   (実プロジェクトでは ``### 1. CONFIG_DB`` のような小見出しの下に bash ブロックを
   並べる runbook が多数派なので、それを満たす形にした)
4. 原因節 — ``## よくある原因`` / ``## 原因`` / ``## 想定原因`` / ``## 想定原因（優先度順）``
5. 関連節 — ``## 関連`` / ``## 関連ページ`` / ``## 関連 reference`` /
   ``## 関連 reference / topics``

Usage:
    python3 meta/scripts/check_runbook_structure.py            # 一覧表示
    python3 meta/scripts/check_runbook_structure.py --check    # CI gate (>0 で exit 1)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_DIR = REPO_ROOT / "docs" / "reference" / "runbooks"

SKIP_FILES = {"index.md"}

SYMPTOM_H2 = {"症状"}
TRIAGE_H2 = {"切り分け", "切り分けフロー", "切り分け手順"}
CMD_H2 = {"確認コマンド", "コマンド", "確認"}
CAUSE_H2 = {"よくある原因", "原因", "想定原因", "想定原因（優先度順）"}
RELATED_H2 = {
    "関連",
    "関連ページ",
    "関連 reference",
    "関連 reference / topics",
}

H2_RE = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
BASH_FENCE_RE = re.compile(r"```(?:bash|sh|shell|console)\b", re.IGNORECASE)


def extract_h2_titles(text: str) -> list[tuple[str, int]]:
    """Return ``[(title, line_index)]`` for every ``## ...`` heading."""
    out: list[tuple[str, int]] = []
    for m in H2_RE.finditer(text):
        out.append((m.group(1).strip(), m.start()))
    return out


def find_section_body(text: str, headings: list[tuple[str, int]], idx: int) -> str:
    """Return the body text of the H2 at ``headings[idx]`` (until next H2 / EOF)."""
    start = headings[idx][1]
    end = headings[idx + 1][1] if idx + 1 < len(headings) else len(text)
    return text[start:end]


def check_runbook(path: Path) -> list[str]:
    """Return the list of *missing* requirement names (empty == OK)."""
    text = path.read_text(encoding="utf-8")
    headings = extract_h2_titles(text)
    titles = {t for t, _ in headings}

    missing: list[str] = []

    if not (titles & SYMPTOM_H2):
        missing.append("症状")

    triage_titles = titles & TRIAGE_H2
    if not triage_titles:
        missing.append("切り分け")

    # 確認コマンド: 明示的な H2 が望ましい。
    # ただし旧テンプレート (``### 1. xxx`` の下に bash ブロックを並べるパターン) は
    # ``--lenient`` 指定時のみ救済する。
    has_cmd_h2 = bool(titles & CMD_H2)
    if not has_cmd_h2:
        missing.append("確認コマンド")

    if not (titles & CAUSE_H2):
        missing.append("原因")

    if not (titles & RELATED_H2):
        missing.append("関連")

    return missing


def collect_runbooks() -> list[Path]:
    if not RUNBOOK_DIR.exists():
        return []
    return sorted(p for p in RUNBOOK_DIR.glob("*.md") if p.name not in SKIP_FILES)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI モード: 不足ページが 1 件でもあれば exit 1",
    )
    args = parser.parse_args()

    runbooks = collect_runbooks()
    bad: list[tuple[Path, list[str]]] = []

    for path in runbooks:
        miss = check_runbook(path)
        if miss:
            bad.append((path, miss))

    rel = lambda p: p.relative_to(REPO_ROOT).as_posix()

    if not bad:
        print(
            f"[check_runbook_structure] OK: {len(runbooks)} runbook(s) all have the 5 required sections."
        )
        return 0

    print(
        f"[check_runbook_structure] {len(bad)} runbook(s) missing required section(s):",
        file=sys.stderr,
    )
    for path, miss in bad:
        print(f"  - {rel(path)}: missing {', '.join(miss)}", file=sys.stderr)

    if args.check:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
