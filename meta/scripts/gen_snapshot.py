#!/usr/bin/env python3
"""Generate docs/_meta/snapshot.md — repository-wide one-page snapshot.

集約する指標:

  - verification 状態の分布 (docs/**/*.md frontmatter `verification`)
  - Topics 22 章の完成度 (sub-page concept/setup/operations/internals/advanced の
    プレースホルダ判定で、`gen_chapter_progress.py` と同じ閾値 100 行)
  - Reference カバレッジ (CLI / CONFIG_DB / YANG のページ数 vs meta/index 総数)
  - 直近 5 round の quality-audit スコア表
  - 各 lint / drift check の検出件数 (informational 含む)
  - 各 Reference (CDB / CLI / YANG) の mermaid カバレッジ
  - glossary 用語数とドキュメント内被リンク数
  - ops-hint カバレッジ (CLI Reference の埋め込み率)
  - last_verified の鮮度分布 (今日 / 7日以内 / 30日以内 / 30日超)
  - 低密度ページ残数 (link-density 報告で密度 < 2 となる対象)
  - backlog 残数 (`meta/backlog/**/*.json` の active 分、`_archived` 除外)

Usage:
    python3 meta/scripts/gen_snapshot.py              # write docs/_meta/snapshot.md
    python3 meta/scripts/gen_snapshot.py --check      # exit 1 on drift

設計方針:

  - 既存の `meta/scripts/gen_*` と同じ idempotent パターン (rewrite + diff)
  - 外部ネットワーク / .cache 依存なし。frontmatter と meta/index/*.json と
    meta/*.md / meta/quality-audit-*.md ファイルから取れるものだけを使う
  - `--check` は 1 日単位で idempotent (last_verified 鮮度バケツが today 基準
    のため、日が変われば自然に再生成が必要になる)
"""
from __future__ import annotations

import argparse
import datetime as _dt
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


def _all_md_files() -> list[Path]:
    return sorted(DOCS.rglob("*.md"))


def count_verification(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for md in files:
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

    out["CONFIG_DB"] = (count_docs("config-db"), 0)

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


def mermaid_coverage() -> dict[str, tuple[int, int]]:
    """Per reference kind, return (pages_with_mermaid, total_pages)."""
    out: dict[str, tuple[int, int]] = {}
    mapping = {"CONFIG_DB": "config-db", "CLI": "cli", "YANG": "yang"}
    for label, sub in mapping.items():
        d = DOCS / "reference" / sub
        if not d.exists():
            out[label] = (0, 0)
            continue
        total = 0
        with_m = 0
        for p in sorted(d.rglob("*.md")):
            if p.name == "index.md" or p.name.startswith("_"):
                continue
            total += 1
            text = p.read_text(encoding="utf-8")
            if "```mermaid" in text:
                with_m += 1
        out[label] = (with_m, total)
    return out


def ops_hint_coverage() -> tuple[int, int]:
    """Return (pages_with_ops_hint, cli_total_pages)."""
    d = DOCS / "reference" / "cli"
    if not d.exists():
        return 0, 0
    total = 0
    hit = 0
    for p in sorted(d.rglob("*.md")):
        if p.name == "index.md" or p.name.startswith("_"):
            continue
        total += 1
        text = p.read_text(encoding="utf-8")
        if "<!-- ops-hint -->" in text:
            hit += 1
    return hit, total


def glossary_metrics(files: list[Path]) -> tuple[int, int]:
    """Return (term_count, inbound_link_count).

    term_count: docs/reference/glossary.md の `### ` 行数 (アンカー単位)。
    inbound_link_count: docs/**/*.md のうち glossary.md へのリンク (URL ベース)
      総出現回数 (1 ファイル内複数リンクも個別カウント)。
    """
    gpath = DOCS / "reference" / "glossary.md"
    term_count = 0
    if gpath.exists():
        for line in gpath.read_text(encoding="utf-8").splitlines():
            if line.startswith("### "):
                term_count += 1
    link_re = re.compile(r"reference/glossary\.md")
    link_count = 0
    for md in files:
        if md.resolve() == gpath.resolve():
            continue
        text = md.read_text(encoding="utf-8")
        link_count += len(link_re.findall(text))
    return term_count, link_count


def last_verified_buckets(files: list[Path], today: _dt.date) -> dict[str, int]:
    """Return counts in buckets: today / within7 / within30 / older / unknown."""
    buckets = {"today": 0, "within7": 0, "within30": 0, "older": 0, "unknown": 0}
    dt_re = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
    for md in files:
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        lv = fm.get("last_verified", "")
        m = dt_re.match(lv)
        if not m:
            buckets["unknown"] += 1
            continue
        try:
            d = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            buckets["unknown"] += 1
            continue
        diff = (today - d).days
        if diff <= 0:
            buckets["today"] += 1
        elif diff <= 7:
            buckets["within7"] += 1
        elif diff <= 30:
            buckets["within30"] += 1
        else:
            buckets["older"] += 1
    return buckets


def recent_audits(n: int = 5) -> list[tuple[int, str]]:
    """Return up to N most recent (round, score_str) tuples, newest first."""
    pat = re.compile(r"quality-audit-(\d+)\.md$")
    rounds: list[tuple[int, Path]] = []
    for p in META.glob("quality-audit-*.md"):
        m = pat.search(p.name)
        if m:
            rounds.append((int(m.group(1)), p))
    rounds.sort(key=lambda x: x[0], reverse=True)
    score_re = re.compile(r"総平均\*?\*?\s*\|\s*\*?\*?([0-9]+\.[0-9]+)")
    out: list[tuple[int, str]] = []
    for n_round, path in rounds[:n]:
        score = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            m = score_re.search(line)
            if m:
                candidate = m.group(1)
                # Phantom-zero guard: see gen_index_banner.extract_average および
                # meta/quality-audit-guide.md §3.2。実 audit の母集団平均は
                # 4.5+/5 帯域に収まっており 0.00 ぴったりは未集計セル混入の
                # phantom entry とみなす。
                if float(candidate) > 0.0:
                    score = candidate
                break
        out.append((n_round, score))
    return out


def _first_int_in_line(line: str) -> int | None:
    m = re.search(r"(\d+)", line)
    return int(m.group(1)) if m else None


def lint_detection_counts() -> list[tuple[str, str]]:
    """Parse lint / informational report files to extract detection counts.

    Returns list of (label, value_str). 該当レポートが無い場合は "—"。
    """
    rows: list[tuple[str, str]] = []

    # frontmatter v2: "Hard violations: N files" / "Warnings (path liveness): N files"
    fv2 = META / "frontmatter-lint-report-v2.md"
    hard = warn = None
    if fv2.exists():
        for line in fv2.read_text(encoding="utf-8").splitlines():
            if "Hard violations" in line:
                hard = _first_int_in_line(line)
            elif "Warnings" in line and "path liveness" in line:
                warn = _first_int_in_line(line)
    rows.append(
        ("frontmatter-lint (hard)", str(hard) if hard is not None else "—")
    )
    rows.append(
        ("frontmatter-lint (warn)", str(warn) if warn is not None else "—")
    )

    # link-density: "- low-density pages: **N**" / "- high-density pages: **N**"
    ld = META / "link-density-report.md"
    low = high = None
    if ld.exists():
        for line in ld.read_text(encoding="utf-8").splitlines():
            if line.startswith("- low-density pages:"):
                low = _first_int_in_line(line)
            elif line.startswith("- high-density pages:"):
                high = _first_int_in_line(line)
    rows.append(("link-density low (<2.0/1k)", str(low) if low is not None else "—"))
    rows.append(("link-density high (>30.0/1k)", str(high) if high is not None else "—"))

    # discrepancy-related-yang: pages without related.yang for discrepancy-found
    drep = META / "discrepancy-related-yang-report.md"
    if drep.exists():
        text = drep.read_text(encoding="utf-8")
        # 探す: "N pages missing" or "0 violations" or summary count of `- docs/`
        m = re.search(r"(\d+)\s*(?:pages|files|violations|missing)", text)
        if m:
            rows.append(("discrepancy-related-yang violations", m.group(1)))
        else:
            rows.append(
                (
                    "discrepancy-related-yang violations",
                    str(sum(1 for ln in text.splitlines() if ln.startswith("- docs/"))),
                )
            )
    else:
        rows.append(("discrepancy-related-yang violations", "—"))

    # empty-related-report: list of `- docs/...` items
    er = META / "empty-related-report.md"
    if er.exists():
        cnt = sum(
            1 for ln in er.read_text(encoding="utf-8").splitlines() if ln.startswith("- docs/")
        )
        rows.append(("related.* empty pages", str(cnt)))
    else:
        rows.append(("related.* empty pages", "—"))

    # daemon-name-violations: list of `- docs/...`
    dnv = META / "daemon-name-violations.md"
    if dnv.exists():
        cnt = sum(
            1 for ln in dnv.read_text(encoding="utf-8").splitlines() if ln.startswith("- docs/")
        )
        rows.append(("daemon-name violations", str(cnt)))
    else:
        rows.append(("daemon-name violations", "—"))

    return rows


def low_density_count() -> int:
    rpt = META / "link-density-report.md"
    if not rpt.exists():
        return 0
    for line in rpt.read_text(encoding="utf-8").splitlines():
        if line.startswith("- low-density pages:"):
            n = _first_int_in_line(line)
            if n is not None:
                return n
    return 0


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


def render(today: _dt.date) -> str:
    files = _all_md_files()
    ver = count_verification(files)
    complete, placeholder, missing = topics_progress()
    refs = reference_coverage()
    audits = recent_audits(5)
    lint_rows = lint_detection_counts()
    mermaid = mermaid_coverage()
    ops_hit, ops_total = ops_hint_coverage()
    g_terms, g_links = glossary_metrics(files)
    buckets = last_verified_buckets(files, today)
    low_dense = low_density_count()
    backlog = backlog_remaining()

    total_pages = ver.get("_total", 0)
    topic_total = complete + placeholder + missing

    lines: list[str] = []
    lines.append("---")
    lines.append("title: スナップショット")
    lines.append("area: meta")
    lines.append("verification: meta")
    lines.append(f"last_verified: {today.isoformat()}")
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

    # last_verified 鮮度
    lines.append("## last_verified 鮮度")
    lines.append("")
    lines.append(f"基準日 **{today.isoformat()}**。")
    lines.append("")
    lines.append("| バケツ | 件数 |")
    lines.append("|---|---:|")
    lines.append(f"| 今日 (0d) | {buckets['today']} |")
    lines.append(f"| 7 日以内 (1-7d) | {buckets['within7']} |")
    lines.append(f"| 30 日以内 (8-30d) | {buckets['within30']} |")
    lines.append(f"| 30 日超 / 古い | {buckets['older']} |")
    lines.append(f"| 不明 / パース不可 | {buckets['unknown']} |")
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

    # Mermaid カバレッジ
    lines.append("## Mermaid カバレッジ (Reference 系)")
    lines.append("")
    lines.append("各 Reference サブツリーで ` ```mermaid ` ブロックを含むページ比率。")
    lines.append("")
    lines.append("| 種別 | mermaid あり | 総ページ | カバレッジ |")
    lines.append("|---|---:|---:|---:|")
    for kind in ("CONFIG_DB", "CLI", "YANG"):
        hit, tot = mermaid.get(kind, (0, 0))
        pct = f"{100.0 * hit / tot:.1f}%" if tot else "—"
        lines.append(f"| {kind} | {hit} | {tot} | {pct} |")
    lines.append("")

    # ops-hint
    lines.append("## ops-hint カバレッジ (CLI Reference)")
    lines.append("")
    pct = f"{100.0 * ops_hit / ops_total:.1f}%" if ops_total else "—"
    lines.append(f"`<!-- ops-hint -->` 埋め込み済み: **{ops_hit} / {ops_total}** ({pct})")
    lines.append("")

    # Glossary
    lines.append("## Glossary")
    lines.append("")
    lines.append("| 項目 | 値 |")
    lines.append("|---|---:|")
    lines.append(f"| 用語数 (`### ` アンカー) | {g_terms} |")
    lines.append(f"| docs 内被リンク数 | {g_links} |")
    lines.append("")

    # 最新 audit (直近 5)
    lines.append("## 直近 5 round quality-audit")
    lines.append("")
    if audits:
        lines.append("| round | 総平均スコア / 5 |")
        lines.append("|---:|---:|")
        for n_round, score in audits:
            lines.append(f"| {n_round} | {score or '—'} |")
        latest = audits[0][0]
        lines.append("")
        lines.append(f"- 最新詳細: `meta/quality-audit-{latest}.md`")
    else:
        lines.append("- audit 未実施")
    lines.append("")

    # Lint / informational detection counts
    lines.append("## Lint / informational 検出件数")
    lines.append("")
    lines.append(
        "各レポート (`meta/*-report*.md` / `meta/*-violations.md`) から抽出した"
        "検出件数。strict / informational を区別せず一覧化する。"
    )
    lines.append("")
    lines.append("| 項目 | 件数 |")
    lines.append("|---|---:|")
    for label, value in lint_rows:
        lines.append(f"| {label} | {value} |")
    lines.append("")

    # その他
    lines.append("## その他指標")
    lines.append("")
    lines.append("| 項目 | 値 |")
    lines.append("|---|---:|")
    lines.append(f"| 低密度ページ残数 (link-density < 2) | {low_dense} |")
    lines.append(f"| backlog 残数 (active) | {backlog} |")
    lines.append("")

    # 関連メタページ (cross-link)
    lines.append("## 関連メタページ")
    lines.append("")
    lines.append(
        "本スナップショットと併読する自動生成メタ系ページ。"
        "それぞれ独立した観点で repo 全体を俯瞰する。"
    )
    lines.append("")
    lines.append("- [residual-tasks](../reference/verification/residual-tasks.md) — verification 残タスク / 未裏取り箇所の一覧")
    lines.append("- [stale-verified](../reference/verification/stale-verified.md) — `last_verified` が古いページ (再裏取り候補)")
    lines.append("- [sources-freshness](../reference/verification/sources-freshness.md) — 引用元 SHA の鮮度 / 参照リポジトリの追従状況")
    lines.append("- [changelog](changelog.md) — 主要変更履歴 (自動生成サマリ含む)")
    lines.append("- [discrepancy-index](../reference/verification/discrepancy-index.md) — HLD と実装の乖離を抽出したインデックス")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 on drift")
    ap.add_argument(
        "--today",
        default=None,
        help="override today (YYYY-MM-DD) for deterministic testing",
    )
    args = ap.parse_args()

    if args.today:
        try:
            today = _dt.date.fromisoformat(args.today)
        except ValueError:
            print(f"[gen_snapshot] invalid --today: {args.today}", file=sys.stderr)
            return 2
    else:
        today = _dt.date.today()

    new_text = render(today)
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
