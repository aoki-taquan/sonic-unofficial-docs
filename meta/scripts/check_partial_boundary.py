#!/usr/bin/env python3
"""Lint that ``monitor: partially_implemented`` pages explicitly delineate
the boundary between *what is implemented* and *what is not yet implemented*.

A "partially implemented" page is only useful to the reader if it spells out
which subset is live on master and which subset is still proposal-only. We
check this by looking for keywords on each side of the boundary:

* implemented-side: 「実装済」「取り込み済」「動く」「動作」「サポート」
  「supported」「implemented」 etc.
* not-implemented-side: 「未実装」「未取り込み」「未対応」「未マージ」
  「not implemented」「not yet」 etc.

If both sides are present, boundary is considered explicit (OK).
If only one side is present, the page is flagged as a warning.
If neither side is present we still flag (rare, picked up by other lints too).

Usage:
    python3 meta/scripts/check_partial_boundary.py            # default report
    python3 meta/scripts/check_partial_boundary.py --check    # informational (exit 0)
    python3 meta/scripts/check_partial_boundary.py --report   # markdown table
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FENCED_CODE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# Phase-like keywords that, when paired with implemented / not-implemented columns
# or cells in a Markdown table, indicate an explicit phase-by-phase boundary.
PHASE_KEYWORDS = [
    r"phase",
    r"フェーズ",
    r"段階",
    r"工程",
    r"ステージ",
    r"stage",
    r"step",
    r"ステップ",
    r"操作",
    r"動作",
    r"処理",
    r"機能",
    r"feature",
    r"項目",
    r"機構",
    r"モード",
    r"mode",
    r"sub.?feature",
]

IMPLEMENTED_PATTERNS = [
    r"実装済",
    r"取り込み済",
    r"取り込まれ(?:て|た)",
    r"マージ済",
    r"マージされ(?:て|た)",
    r"動作する",
    r"動作確認",
    r"動作している",
    r"動く",
    r"サポート(?:され|済)",
    r"対応済",
    r"supported",
    r"implemented",
    r"available\s+on\s+master",
    r"merged",
    r"shipped",
    r"landed",
]

NOT_IMPLEMENTED_PATTERNS = [
    r"未実装",
    r"未取り込み",
    r"未対応",
    r"未\s*マージ",
    r"未サポート",
    r"対応\s*PR\s*(?:無し|なし|未マージ|未取り込み)",
    r"実装されていな",
    r"取り込まれていな",
    r"マージされていな",
    r"欠落",
    r"not\s+implemented",
    r"not\s+yet",
    r"missing",
    r"unsupported",
    r"todo",
]


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm, text[m.end():]


def strip_noise(body: str) -> str:
    body = HTML_COMMENT_RE.sub("", body)
    body = FENCED_CODE_RE.sub("", body)
    body = INLINE_CODE_RE.sub("", body)
    return body


def has_any(body: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if re.search(pat, body, flags=re.IGNORECASE):
            return True
    return False


TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")


def extract_tables(body: str) -> list[list[list[str]]]:
    """Extract Markdown pipe tables from body as lists of rows-of-cells.

    A table is recognized by a header row, a separator row of dashes, and one
    or more data rows. Cells are stripped.
    """
    tables: list[list[list[str]]] = []
    lines = body.splitlines()
    i = 0
    n = len(lines)
    while i < n - 1:
        if TABLE_ROW_RE.match(lines[i]) and TABLE_SEP_RE.match(lines[i + 1]):
            # collect contiguous pipe rows from header onward
            rows: list[list[str]] = []
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows.append(header)
            j = i + 2
            while j < n and TABLE_ROW_RE.match(lines[j]):
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                rows.append(cells)
                j += 1
            if len(rows) >= 2:
                tables.append(rows)
            i = j
            continue
        i += 1
    return tables


def has_phase_boundary_table(body: str) -> bool:
    """Return True if body contains a Markdown table that has both
    implemented-side and not-implemented-side keywords AND a phase-like keyword
    somewhere in its cells (header or body). This represents an explicit
    phase-by-phase boundary table, which is the most actionable form of
    "実装済 / 未実装" delineation per guide §5.2.
    """
    for rows in extract_tables(body):
        flat_cells = [cell for row in rows for cell in row]
        text = "\n".join(flat_cells)
        # all three must coexist within the same table
        if (
            has_any(text, PHASE_KEYWORDS)
            and has_any(text, IMPLEMENTED_PATTERNS)
            and has_any(text, NOT_IMPLEMENTED_PATTERNS)
        ):
            return True
    return False


def check_body(body: str) -> tuple[bool, str]:
    cleaned = strip_noise(body)
    # 1) Phase-boundary table form (guide §5.2 recommended form): a Markdown
    #    table that explicitly enumerates phases / operations alongside
    #    implemented vs not-implemented cells. Treat as OK regardless of
    #    surrounding prose keywords.
    if has_phase_boundary_table(cleaned):
        return True, ""
    # 2) Fall back to free-prose keyword pairing (legacy rule)
    impl = has_any(cleaned, IMPLEMENTED_PATTERNS)
    not_impl = has_any(cleaned, NOT_IMPLEMENTED_PATTERNS)
    if impl and not_impl:
        return True, ""
    if impl and not not_impl:
        return False, "missing not-implemented-side keywords"
    if not_impl and not impl:
        return False, "missing implemented-side keywords"
    return False, "missing both implemented-side and not-implemented-side keywords"


def collect() -> list[dict[str, str]]:
    suspects: list[dict[str, str]] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(md.relative_to(REPO_ROOT))
        text = md.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if fm.get("monitor") != "partially_implemented":
            continue
        ok, reason = check_body(body)
        if ok:
            continue
        suspects.append({"path": rel, "reason": reason})
    return suspects


def render_report(suspects: list[dict[str, str]]) -> str:
    if not suspects:
        return "No partial-boundary suspects found.\n"
    lines = [
        "# partial-boundary report\n",
        f"Total suspects: {len(suspects)}\n",
        "| Path | reason |",
        "|---|---|",
    ]
    for s in suspects:
        lines.append(f"| `{s['path']}` | {s['reason']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="informational mode (count to stderr, exit 0)")
    ap.add_argument("--report", action="store_true",
                    help="print markdown table of suspects to stdout")
    args = ap.parse_args()

    suspects = collect()

    if args.report:
        print(render_report(suspects))
    elif args.check:
        print(f"partial-boundary suspects: {len(suspects)}", file=sys.stderr)
        for s in suspects[:30]:
            print(f"  {s['path']} -- {s['reason']}", file=sys.stderr)
        if len(suspects) > 30:
            print(f"  ... and {len(suspects) - 30} more", file=sys.stderr)
        return 0  # informational — always exit 0
    else:
        print(f"partial-boundary suspects: {len(suspects)}")
        for s in suspects[:30]:
            print(f"  {s['path']} -- {s['reason']}")
        if len(suspects) > 30:
            print(f"  ... and {len(suspects) - 30} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
