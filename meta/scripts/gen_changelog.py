#!/usr/bin/env python3
"""Generate docs/_meta/changelog.md from merged PR metadata.

`gh pr list --state merged` で取得した PR 一覧を mergedAt 降順・月単位で
グルーピングし、`docs/_meta/changelog.md` を機械生成する。

Usage:
    python3 meta/scripts/gen_changelog.py            # 書き出し
    python3 meta/scripts/gen_changelog.py --check    # drift 検知（informational, soft check）

`--check` モードでは現在の出力と既存ファイルを比較して、差分があれば
標準出力に通知する。CI 上では soft check（exit 0）にとどめる。
ローカルで強制的に exit 1 させたい場合は `--strict` を併用する。

このスクリプトは `gh` CLI が認証済み（`gh auth status` が OK）の前提で動く。
gh が無い・認証されていない場合は `git log --merges --first-parent main` を
フォールバックとして使う（label 情報は取得できない）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "docs" / "_meta" / "changelog.md"

FRONTMATTER = """---
title: 変更履歴
description: "変更履歴 — このページは merged PR のメタデータから meta/scripts/gen_changelog.py で機械生成されています。手で編集しないでください。"
verification: meta
last_verified: {date}
tags:
  - changelog
  - meta
---
"""

HEADER_BODY = """
# 変更履歴

!!! warning "機械生成ページ"
    このページは `meta/scripts/gen_changelog.py` が GitHub の merged PR 一覧から
    生成しています。**手で編集しないでください**。再生成するたびに上書きされます。

    定期実行手順は `meta/discrepancy-operations.md` を参照してください。

merged PR を `mergedAt` 降順・月単位でグルーピングして並べています。
各エントリの形式は `- YYYY-MM-DD #N <title> [labels]` です。

"""


def run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def fetch_via_gh(limit: int = 500) -> list[dict] | None:
    """`gh pr list` で merged PR を取得。失敗時は None。"""
    if shutil.which("gh") is None:
        return None
    code, out, err = run([
        "gh", "pr", "list",
        "--state", "merged",
        "--limit", str(limit),
        "--json", "number,title,mergedAt,labels",
    ])
    if code != 0:
        sys.stderr.write(f"[gen_changelog] gh failed: {err}\n")
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[gen_changelog] JSON decode error: {e}\n")
        return None
    prs = []
    for item in data:
        merged_at = item.get("mergedAt")
        if not merged_at:
            continue
        labels = [lb.get("name", "") for lb in (item.get("labels") or [])]
        prs.append({
            "number": item.get("number"),
            "title": (item.get("title") or "").strip(),
            "mergedAt": merged_at,
            "labels": [lb for lb in labels if lb],
        })
    return prs


def fetch_via_git() -> list[dict]:
    """git log --merges fallback。label は空。"""
    code, out, _ = run([
        "git", "log", "--merges", "--first-parent", "main",
        "--pretty=format:%H%x09%cI%x09%s",
    ])
    if code != 0:
        return []
    prs: list[dict] = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        _, iso, subject = parts
        # subject: "Merge pull request #NNN from ..." を期待
        num = None
        title = subject
        if subject.startswith("Merge pull request #"):
            try:
                rest = subject[len("Merge pull request #"):]
                num_s, _ = rest.split(" ", 1)
                num = int(num_s)
            except (ValueError, IndexError):
                pass
        # squash merge は --merges に出ないので、見つかった分のみ
        prs.append({
            "number": num,
            "title": title,
            "mergedAt": iso,
            "labels": [],
        })
    return prs


def parse_iso(s: str) -> datetime:
    # gh が返す形式: "2026-05-11T12:34:56Z"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def render(prs: list[dict]) -> str:
    prs_sorted = sorted(prs, key=lambda p: parse_iso(p["mergedAt"]), reverse=True)
    groups: dict[str, list[dict]] = defaultdict(list)
    for pr in prs_sorted:
        dt = parse_iso(pr["mergedAt"])
        key = dt.strftime("%Y-%m")
        groups[key].append(pr)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = [FRONTMATTER.format(date=today), HEADER_BODY]

    if not prs_sorted:
        out.append("（merged PR が見つかりませんでした。）\n")
    else:
        out.append(f"集計対象: {len(prs_sorted)} PR\n\n")
        for month in sorted(groups.keys(), reverse=True):
            out.append(f"## {month}\n\n")
            for pr in groups[month]:
                dt = parse_iso(pr["mergedAt"]).strftime("%Y-%m-%d")
                num = pr["number"]
                num_s = f"#{num}" if num is not None else "(no-num)"
                title = pr["title"].replace("\n", " ").replace("|", "\\|")
                labels = pr["labels"]
                label_s = f" [{', '.join(labels)}]" if labels else ""
                out.append(f"- {dt} {num_s} {title}{label_s}\n")
            out.append("\n")

    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="既存ファイルと差分があるか確認するだけ（soft check）")
    ap.add_argument("--strict", action="store_true",
                    help="--check 時に差分があれば exit 1（CI では非推奨）")
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args()

    prs = fetch_via_gh(limit=args.limit)
    if prs is None:
        sys.stderr.write("[gen_changelog] gh CLI 不可。git log にフォールバック。\n")
        prs = fetch_via_git()
    content = render(prs)

    if args.check:
        existing = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if existing == content:
            print(f"[gen_changelog] OK: {OUTPUT.relative_to(REPO_ROOT)} は最新です。")
            return 0
        # 差分のサマリだけ表示
        existing_lines = existing.splitlines()
        new_lines = content.splitlines()
        print(f"[gen_changelog] DRIFT: {OUTPUT.relative_to(REPO_ROOT)} に差分があります。")
        print(f"  既存: {len(existing_lines)} 行, 新規: {len(new_lines)} 行")
        print("  再生成するには: python3 meta/scripts/gen_changelog.py")
        return 1 if args.strict else 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"[gen_changelog] wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(prs)} PR)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
