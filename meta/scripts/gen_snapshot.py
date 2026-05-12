#!/usr/bin/env python3
"""Generate docs/_meta/snapshot.md — repository-wide one-page snapshot.

集約する指標:

  - verification 状態の分布 (docs/**/*.md frontmatter `verification`)
  - Topics 22 章の完成度 (sub-page concept/setup/operations/internals/advanced の
    プレースホルダ判定で、`gen_chapter_progress.py` と同じ閾値 100 行)
  - Reference カバレッジ (CLI / CONFIG_DB / YANG のページ数 vs meta/index 総数)
  - 最新 quality-audit (round 番号 + 総平均スコア)
  - 低密度ページ残数 (link-density 報告で密度 < 2 となる対象)
  - backlog 残数 (`meta/backlog/**/*.json` の active 分、`_archived` 除外)

Usage:
    python3 meta/scripts/gen_snapshot.py              # write docs/_meta/snapshot.md
    python3 meta/scripts/gen_snapshot.py --check      # exit 1 on drift

設計方針:

  - 既存の `meta/scripts/gen_*` と同じ idempotent パターン (rewrite + diff)
  - 外部ネットワーク / .cache 依存なし。frontmatter と meta/index/*.json と
    quality-audit-*.md ファイル名から取れるものだけを使う
  - 日付や `last_verified` 等の揺らぐ値は表に出さない (drift 安定性のため)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
META = ROOT / "meta"
OUTPUT = DOCS / "_meta" / "snapshot.md"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

VERIFICATION_STATES = [
    "code-verified",
    "runbook-verified",
    "discrepancy-found",
    "issue-confirmed",
    "hld-only",
    "meta",
    "stub",
]

TOPICS_DIR = DOCS / "topics"
SUBPAGES = ["concept.md", "setup.md", "operations.md", "internals.md", "advanced.md"]
PLACEHOLDER_LINE_THRESHOLD = 100  # gen_chapter_progress.py と一致


def parse_frontmatter(text: str) -> dict[str, str]:
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


def count_verification() -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for md in DOCS.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        state = fm.get("verification", "stub") or "stub"
        if state not in VERIFICATION_STATES:
            state = "stub"
        counts[state] += 1
    counts["_total"] = sum(counts[s] for s in VERIFICATION_STATES)
    return counts


def body_line_count(md: Path) -> int:
    text = md.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    body = text[m.end():] if m else text
    return len([ln for ln in body.splitlines() if ln.strip()])


def topics_progress() -> tuple[int, int, int]:
    """Return (complete, placeholder, missing) sub-page counts across all chapters."""
    complete = placeholder = missing = 0
    if not TOPICS_DIR.exists():
        return 0, 0, 0
    for chapter_dir in sorted(TOPICS_DIR.iterdir()):
        if not chapter_dir.is_dir():
            continue
        for sub in SUBPAGES:
            p = chapter_dir / sub
            if not p.exists():
                missing += 1
            elif body_line_count(p) < PLACEHOLDER_LINE_THRESHOLD:
                placeholder += 1
            else:
                complete += 1
    return complete, placeholder, missing


def reference_coverage() -> dict[str, tuple[int, int]]:
    """For each ref kind, return (pages_in_docs, items_in_index)."""
    out: dict[str, tuple[int, int]] = {}

    def count_docs(subdir: str) -> int:
        d = DOCS / "reference" / subdir
        if not d.exists():
            return 0
        return sum(1 for p in d.rglob("*.md") if p.name != "index.md" and not p.name.startswith("_"))

    # CLI — meta/index/cli.json は flat list。kind=="command" のみ集計
    cli_idx = META / "index" / "cli.json"
    cli_total = 0
    try:
        cli_data = json.loads(cli_idx.read_text(encoding="utf-8"))
        if isinstance(cli_data, list):
            cli_total = sum(1 for e in cli_data if e.get("kind") == "command")
        elif isinstance(cli_data, dict):
            cli_total = len(cli_data.get("commands", []))
    except Exception:
        cli_total = 0
    out["CLI"] = (count_docs("cli"), cli_total)

    # CONFIG_DB — 索引 json 未整備。`docs/reference/config-db` のページ数のみ表示
    out["CONFIG_DB"] = (count_docs("config-db"), 0)

    # YANG
    yang_idx = META / "index" / "yang.json"
    try:
        yang_data = json.loads(yang_idx.read_text(encoding="utf-8"))
        if isinstance(yang_data, dict):
            yang_total = len(yang_data.get("modules", yang_data))
        else:
            yang_total = len(yang_data)
    except Exception:
        yang_total = 0
    out["YANG"] = (count_docs("yang"), yang_total)

    return out


def latest_audit() -> tuple[int, str]:
    """Return (round_number, mean_score_str). Empty string if not extractable."""
    pat = re.compile(r"quality-audit-(\d+)\.md$")
    rounds: list[tuple[int, Path]] = []
    for p in META.glob("quality-audit-*.md"):
        m = pat.search(p.name)
        if m:
            rounds.append((int(m.group(1)), p))
    if not rounds:
        return 0, ""
    n, path = max(rounds, key=lambda x: x[0])
    score_re = re.compile(r"総平均\*?\*?\s*\|\s*\*?\*?([0-9]+\.[0-9]+)")
    score = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        m = score_re.search(line)
        if m:
            score = m.group(1)
            break
    return n, score


def low_density_count() -> int:
    """Count low-density pages from latest link-density report (best-effort).

    `meta/link-density-report.md` の "低密度" 行を数える。生成が古い場合は 0。
    """
    rpt = META / "link-density-report.md"
    if not rpt.exists():
        return 0
    text = rpt.read_text(encoding="utf-8")
    # 表行 "| docs/... | 1.23 |" のうち低密度セクション配下を数える
    in_low = False
    cnt = 0
    for line in text.splitlines():
        if line.startswith("## "):
            in_low = "低密度" in line or "low" in line.lower()
            continue
        if in_low and line.startswith("| docs/"):
            cnt += 1
    return cnt


def backlog_remaining() -> int:
    bdir = META / "backlog"
    if not bdir.exists():
        return 0
    cnt = 0
    for p in bdir.rglob("*.json"):
        if "_archived" in p.parts:
            continue
        cnt += 1
    return cnt


def render() -> str:
    ver = count_verification()
    complete, placeholder, missing = topics_progress()
    refs = reference_coverage()
    round_n, score = latest_audit()
    low_dense = low_density_count()
    backlog = backlog_remaining()

    total_pages = ver.get("_total", 0)
    topic_total = complete + placeholder + missing

    lines: list[str] = []
    lines.append("---")
    lines.append("title: スナップショット")
    lines.append("area: meta")
    lines.append("verification: meta")
    lines.append("last_verified: 2026-05-12")
    lines.append("sources: []")
    lines.append("---")
    lines.append("")
    lines.append("# スナップショット")
    lines.append("")
    lines.append(
        "リポジトリ全体の状態を 1 ページに集約した自動生成サマリ。"
        "個別の詳細は `coverage.md` / `sitemap.md` / `discrepancies.md` を参照。"
    )
    lines.append("")
    lines.append("!!! note \"生成元\"")
    lines.append("    `python3 meta/scripts/gen_snapshot.py` で再生成。")
    lines.append("    `--check` で drift 検出 (CI integration 用)。")
    lines.append("")

    # Verification 分布
    lines.append("## verification 分布")
    lines.append("")
    lines.append(f"全 **{total_pages}** ページ。")
    lines.append("")
    lines.append("| verification | 件数 |")
    lines.append("|---|---:|")
    for s in VERIFICATION_STATES:
        lines.append(f"| {s} | {ver.get(s, 0)} |")
    lines.append(f"| **合計** | **{total_pages}** |")
    lines.append("")

    # Topics 完成度
    lines.append("## Topics 22 章 sub-page 完成度")
    lines.append("")
    lines.append(
        f"5 種 (concept/setup/operations/internals/advanced) × 22 章 = 110 想定。"
        f"閾値: 本文 {PLACEHOLDER_LINE_THRESHOLD} 行未満は placeholder 扱い。"
    )
    lines.append("")
    lines.append("| 状態 | 件数 |")
    lines.append("|---|---:|")
    lines.append(f"| 完成 | {complete} |")
    lines.append(f"| placeholder | {placeholder} |")
    lines.append(f"| 欠落 | {missing} |")
    lines.append(f"| **合計** | **{topic_total}** |")
    lines.append("")

    # Reference カバレッジ
    lines.append("## Reference カバレッジ")
    lines.append("")
    lines.append("| 種別 | 公開ページ | 索引総数 | カバレッジ |")
    lines.append("|---|---:|---:|---:|")
    for kind in ("CLI", "CONFIG_DB", "YANG"):
        pages, total = refs.get(kind, (0, 0))
        if total:
            pct = f"{100.0 * pages / total:.1f}%"
            total_cell = str(total)
        else:
            pct = "—"
            total_cell = "—"
        lines.append(f"| {kind} | {pages} | {total_cell} | {pct} |")
    lines.append("")

    # 最新 audit
    lines.append("## 最新 quality-audit")
    lines.append("")
    if round_n:
        score_part = f"総平均スコア **{score} / 5**" if score else "(スコア抽出不可)"
        lines.append(f"- round **{round_n}** — {score_part}")
        lines.append(f"- 詳細: `meta/quality-audit-{round_n}.md`")
    else:
        lines.append("- audit 未実施")
    lines.append("")

    # その他
    lines.append("## その他指標")
    lines.append("")
    lines.append("| 項目 | 値 |")
    lines.append("|---|---:|")
    lines.append(f"| 低密度ページ残数 (link-density < 2) | {low_dense} |")
    lines.append(f"| backlog 残数 (active) | {backlog} |")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 on drift")
    args = ap.parse_args()

    new_text = render()
    if args.check:
        if not OUTPUT.exists():
            print(f"[gen_snapshot] missing {OUTPUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        old = OUTPUT.read_text(encoding="utf-8")
        if old != new_text:
            print(f"[gen_snapshot] drift detected in {OUTPUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("[gen_snapshot] up to date")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(new_text, encoding="utf-8")
    print(f"[gen_snapshot] wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
