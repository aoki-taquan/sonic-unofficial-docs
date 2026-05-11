#!/usr/bin/env python3
"""Compute link density per docs page and report low-density pages.

Definition
----------
Link density (links per 1000 chars of body text) is computed by:

* stripping the YAML frontmatter
* stripping fenced code blocks (``` ... ```) and indented code blocks
* stripping HTML comments
* stripping the auto-generated tails (next-reads, related, evidence-rendered,
  glossary-links-injected marker)
* counting Markdown links ``[text](url)`` in the remaining body
* dividing by ``max(1, len(body_chars)) / 1000``

Pages with **at least 600 body chars** and density below ``--threshold``
(default 6.0 links / 1000 chars) are reported as "low density".

Output
------
``--report``  : write Markdown report to ``meta/link-density-report.md``
                with a table of low-density pages (highest body length first)
                and overall stats.
default       : print summary to stdout, exit 0.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
REPORT_PATH = ROOT / "meta" / "link-density-report.md"

EXCLUDE_DIRS = {"reference", "_meta", "categories", "guides"}

FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
NEXT_READS_RE = re.compile(
    r"<!-- next-reads:start -->.*?<!-- next-reads:end -->", re.DOTALL
)
EVIDENCE_RE = re.compile(
    r"<!-- evidence-rendered:start -->.*?<!-- evidence-rendered:end -->", re.DOTALL
)
LINK_RE = re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)")
INDENTED_CODE_RE = re.compile(r"(?m)^( {4}|\t).*$")


def strip_body(text: str) -> str:
    text = FRONTMATTER_RE.sub("", text, count=1)
    text = NEXT_READS_RE.sub("", text)
    text = EVIDENCE_RE.sub("", text)
    text = FENCED_CODE_RE.sub("", text)
    text = HTML_COMMENT_RE.sub("", text)
    text = INDENTED_CODE_RE.sub("", text)
    return text


def page_stats(md_path: Path) -> tuple[int, int, float]:
    raw = md_path.read_text(encoding="utf-8")
    body = strip_body(raw)
    chars = len(body)
    links = len(LINK_RE.findall(body))
    density = (links / max(1, chars)) * 1000.0
    return chars, links, density


def iter_pages():
    for p in DOCS.rglob("*.md"):
        rel = p.relative_to(DOCS)
        if rel.parts[0] in EXCLUDE_DIRS:
            continue
        if rel.name == "index.md":
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=6.0,
                    help="density threshold (links per 1000 chars)")
    ap.add_argument("--min-chars", type=int, default=600,
                    help="ignore pages shorter than this body length")
    ap.add_argument("--report", action="store_true",
                    help="write Markdown report to meta/link-density-report.md")
    ap.add_argument("--top", type=int, default=0,
                    help="if >0, only include top N lowest-density pages")
    args = ap.parse_args()

    rows = []
    total_chars = 0
    total_links = 0
    for md in iter_pages():
        chars, links, density = page_stats(md)
        total_chars += chars
        total_links += links
        if chars < args.min_chars:
            continue
        if density < args.threshold:
            rows.append((md, chars, links, density))

    # Sort: largest body first (most "expensive" to leave under-linked)
    rows.sort(key=lambda r: (-r[1], r[3]))

    if args.top > 0:
        rows = rows[: args.top]

    avg_density = (total_links / max(1, total_chars)) * 1000.0

    summary = (
        f"pages_scanned={sum(1 for _ in iter_pages())} "
        f"low_density={len(rows)} "
        f"threshold={args.threshold} "
        f"avg_density={avg_density:.2f}/1000ch"
    )

    if args.report:
        lines = [
            "# Link density report",
            "",
            f"- 走査対象: `docs/**/*.md` (除外 dir: {sorted(EXCLUDE_DIRS)})",
            f"- リンク密度 = 本文 1000 文字あたりの Markdown link `[..](..)` 数",
            f"- しきい値: **{args.threshold:.1f}** / 1000ch (本文 {args.min_chars} 文字以上のページが対象)",
            f"- 全体平均: **{avg_density:.2f}** / 1000ch",
            f"- 低密度ページ件数: **{len(rows)}**",
            "",
            "| # | path | chars | links | density |",
            "|---:|------|------:|------:|--------:|",
        ]
        for i, (p, chars, links, density) in enumerate(rows, 1):
            rel = p.relative_to(ROOT)
            lines.append(
                f"| {i} | `{rel}` | {chars} | {links} | {density:.2f} |"
            )
        REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {REPORT_PATH.relative_to(ROOT)} ({summary})")
    else:
        print(summary)
        for p, chars, links, density in rows[:20]:
            print(f"  {density:5.2f}/1000ch  chars={chars:5d} links={links:3d}  "
                  f"{p.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
