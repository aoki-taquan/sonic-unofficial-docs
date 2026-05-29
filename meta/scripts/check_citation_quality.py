#!/usr/bin/env python3
"""Detect verified pages that lack any citation (footnote or evidence block).

`verification` が `code-verified` / `runbook-verified` / `discrepancy-found` の
ページなのに、本文中に脚注 (`[^N]: ...`) も `<!-- evidence: ... -->` ブロックも
無いページを **citation-deficient** として検知する informational lint。

裏取り済みを名乗りつつ典拠が本文に紐づかないページを発見し、Verifier の再裏取り
候補に提供する。

Usage:
    python3 meta/scripts/check_citation_quality.py
    python3 meta/scripts/check_citation_quality.py --check   # CI informational
    python3 meta/scripts/check_citation_quality.py --report  # 詳細 TSV
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
EXCEPTIONS = REPO_ROOT / "meta" / "citation-quality-exceptions.json"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
FOOTNOTE_DEF_RE = re.compile(r"^\[\^[^\]]+\]:\s", re.MULTILINE)
EVIDENCE_RE = re.compile(r"<!--\s*evidence:", re.IGNORECASE)

TARGET_STATUSES = {"code-verified", "runbook-verified", "discrepancy-found"}

# 既定で評価対象に含めない area プレフィックス。
# Reference 系 (CLI / CONFIG_DB / YANG ref) は生成テーブル中心で脚注を本文に
# 書く設計ではないため、デフォルトで除外する。runbooks は手書きの手順書なので
# 評価対象に残す。
DEFAULT_AREA_SKIP_PREFIXES = (
    "docs/reference/cli/",
    "docs/reference/config-db/",
    "docs/reference/yang/",
    "docs/reference/verification/",
    "docs/_meta/",
    "docs/categories/",
    "docs/guides/",
)

# Reference 配下でも個別ファイルとして除外したいページ。
DEFAULT_PATH_SKIP = {
    "docs/reference/index.md",
    "docs/reference/glossary.md",
    "docs/reference/config-db-orch-map.md",
    # sai-attributes は SAI ヘッダ参照の早見表で、表ごとに `(saiXxx.h)` 等の
    # in-line 出典が並ぶ設計のため脚注は不要。
    "docs/reference/sai-attributes.md",
}


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


def load_exceptions() -> set[str]:
    if not EXCEPTIONS.exists():
        return set()
    try:
        data = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return set(data.get("exceptions", []))


def has_citation(body: str) -> bool:
    if FOOTNOTE_DEF_RE.search(body):
        return True
    if EVIDENCE_RE.search(body):
        return True
    return False


def collect(include_reference: bool = False) -> list[dict[str, object]]:
    exceptions = load_exceptions()
    rows: list[dict[str, object]] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(md.relative_to(REPO_ROOT))
        if not include_reference:
            if rel.startswith(DEFAULT_AREA_SKIP_PREFIXES):
                continue
            if rel in DEFAULT_PATH_SKIP:
                continue
        if rel in exceptions:
            continue
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        verification = (fm.get("verification") or "").strip()
        if verification not in TARGET_STATUSES:
            continue
        # body = frontmatter 以降
        m = FRONTMATTER_RE.match(text)
        body = text[m.end():] if m else text
        if has_citation(body):
            continue
        rows.append(
            {
                "path": rel,
                "verification": verification,
                "title": fm.get("title", ""),
                "area": fm.get("area", ""),
                "body_chars": len(body),
            }
        )
    rows.sort(key=lambda r: r["body_chars"], reverse=True)
    return rows


def render_tsv(rows: list[dict[str, object]]) -> str:
    out = ["path\tverification\tarea\tbody_chars\ttitle"]
    for r in rows:
        out.append(
            f"{r['path']}\t{r['verification']}\t{r['area']}\t{r['body_chars']}\t{r['title']}"
        )
    return "\n".join(out)


def render_report(rows: list[dict[str, object]]) -> str:
    lines: list[str] = []
    lines.append(f"# citation-deficient pages: {len(rows)}")
    lines.append("")
    lines.append(
        "verification が code-verified / runbook-verified / discrepancy-found "
        "なのに本文中に脚注 (`[^N]`) も `<!-- evidence:` ブロックも無いページ。"
    )
    lines.append("")
    lines.append("| path | verification | area | body_chars |")
    lines.append("|------|--------------|------|-----------:|")
    for r in rows:
        lines.append(
            f"| `{r['path']}` | {r['verification']} | {r['area']} | {r['body_chars']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI informational モード。件数を stderr に出して 0 で終了する。",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="citation 不足ページがあれば 1 で終了する (CI strict ゲート用)。",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Markdown 形式の詳細レポートを stdout に出す。",
    )
    parser.add_argument(
        "--include-reference",
        action="store_true",
        help="Reference 系 (default 除外) も評価対象に含める。",
    )
    args = parser.parse_args()

    rows = collect(include_reference=args.include_reference)

    if args.check:
        print(
            f"[citation-quality] {len(rows)} citation-deficient page(s) "
            f"(verification in {sorted(TARGET_STATUSES)}, informational)",
            file=sys.stderr,
        )
        return 0

    if args.strict:
        if rows:
            print(
                f"[citation-quality] {len(rows)} citation-deficient page(s) "
                f"(verification in {sorted(TARGET_STATUSES)}, strict):",
                file=sys.stderr,
            )
            for r in rows:
                print(f"  - {r[0]}", file=sys.stderr)
            return 1
        print("[citation-quality] OK (no citation-deficient pages)", file=sys.stderr)
        return 0

    if args.report:
        print(render_report(rows))
        return 0

    print(render_tsv(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
