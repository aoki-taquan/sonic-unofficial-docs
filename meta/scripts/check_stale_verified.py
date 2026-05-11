#!/usr/bin/env python3
"""Detect docs/**/*.md pages whose ``last_verified`` is older than a threshold.

90 日以上裏取りが古いページを一覧する informational ツール。

Usage:
    python3 meta/scripts/check_stale_verified.py
    python3 meta/scripts/check_stale_verified.py --threshold-days 60 --max-list 100
    python3 meta/scripts/check_stale_verified.py --check        # CI informational
    python3 meta/scripts/check_stale_verified.py --write        # 機械生成ページを書く
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
OUTPUT = DOCS_DIR / "reference" / "verification" / "stale-verified.md"

# プロジェクト固定の「今日」。CLAUDE.md / 他スクリプトと一貫させる。
TODAY = _dt.date(2026, 5, 11)

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    """gen_coverage.py と同形式の簡易 frontmatter parser。"""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def _parse_date(s: str) -> _dt.date | None:
    s = s.strip().strip('"').strip("'")
    if not s:
        return None
    try:
        return _dt.date.fromisoformat(s)
    except ValueError:
        return None


def collect(threshold_days: int) -> list[dict[str, object]]:
    """threshold_days を超えて古いページの情報を集める。"""
    rows: list[dict[str, object]] = []
    # meta / stub ステータスは informational 対象外（運用ページや雛形）
    skip_states = {"meta", "stub"}
    for md in sorted(DOCS_DIR.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        verification = fm.get("verification", "") or ""
        if verification in skip_states:
            continue
        last_verified = _parse_date(fm.get("last_verified", ""))
        if last_verified is None:
            continue
        delta = (TODAY - last_verified).days
        if delta < threshold_days:
            continue
        rows.append(
            {
                "path": str(md.relative_to(REPO_ROOT)),
                "last_verified": last_verified.isoformat(),
                "days": delta,
                "verification": verification or "(unset)",
                "monitor": fm.get("monitor", "") or "-",
            }
        )
    rows.sort(key=lambda r: r["days"], reverse=True)
    return rows


def render_tsv(rows: list[dict[str, object]], max_list: int) -> str:
    out: list[str] = []
    out.append("path\tlast_verified\tdays-since\tverification\tmonitor")
    for r in rows[:max_list]:
        out.append(
            f"{r['path']}\t{r['last_verified']}\t{r['days']}\t{r['verification']}\t{r['monitor']}"
        )
    return "\n".join(out)


def render_md_page(rows: list[dict[str, object]], threshold_days: int, max_list: int) -> str:
    lines: list[str] = []
    lines.append("---")
    lines.append("title: 古い裏取りページ")
    lines.append(
        'description: "古い裏取りページ — last_verified が一定期間以上更新されていないページを一覧する。Verifier 再裏取りのトリガに用いる。"'
    )
    lines.append("verification: meta")
    lines.append("last_verified: 2026-05-11")
    lines.append("tags: [verification, stale]")
    lines.append("---")
    lines.append("")
    lines.append("# 古い裏取りページ")
    lines.append("")
    lines.append(
        f"本ページは `docs/**/*.md` の frontmatter `last_verified` を見て、"
        f"基準日 **{TODAY.isoformat()}** から **{threshold_days} 日以上** 経過した"
        "ページを一覧する。`meta/scripts/check_stale_verified.py --write` で自動生成される。"
    )
    lines.append("")
    lines.append(
        "対象は `verification` が `meta` / `stub` 以外のページ。"
        "上位 " + str(max_list) + " 件まで表示する。"
    )
    lines.append("")
    lines.append("## 再裏取りトリガ")
    lines.append("")
    lines.append(
        "本ページに掲載されたページは Verifier の再裏取り候補になる。"
        "詳細な運用手順は `meta/discrepancy-operations.md` および "
        "`meta/prompts/verifier.md` を参照（リポジトリ内）。"
    )
    lines.append("")
    lines.append(f"全 **{len(rows)}** ページが基準を満たした（しきい値 {threshold_days} 日）。")
    lines.append("")
    if not rows:
        lines.append("現在、しきい値を超えるページはない。")
        lines.append("")
        return "\n".join(lines)

    lines.append("## 上位 " + str(min(max_list, len(rows))) + " 件")
    lines.append("")
    lines.append("| path | last_verified | days-since | verification | monitor |")
    lines.append("|------|---------------|-----------:|--------------|---------|")
    for r in rows[:max_list]:
        # docs/ 以下のパスは MkDocs リンクにできる
        path = str(r["path"])
        if path.startswith("docs/") and path.endswith(".md"):
            link_target = path[len("docs/"):]
            path_cell = f"[`{path}`](/{link_target[:-3]}/)"
        else:
            path_cell = f"`{path}`"
        lines.append(
            f"| {path_cell} | {r['last_verified']} | {r['days']} | "
            f"{r['verification']} | {r['monitor']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold-days", type=int, default=90)
    parser.add_argument("--max-list", type=int, default=50)
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI informational モード。件数を stderr に出して 0 で終了する。",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="docs/reference/verification/stale-verified.md を書き出す。",
    )
    args = parser.parse_args()

    rows = collect(args.threshold_days)

    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        new_text = render_md_page(rows, args.threshold_days, args.max_list)
        OUTPUT.write_text(new_text, encoding="utf-8")
        print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(rows)} stale pages)")
        return 0

    if args.check:
        print(
            f"[stale-verified] {len(rows)} page(s) older than "
            f"{args.threshold_days} days (informational)",
            file=sys.stderr,
        )
        return 0

    print(render_tsv(rows, args.max_list))
    return 0


if __name__ == "__main__":
    sys.exit(main())
