#!/usr/bin/env python3
"""Measure link density of every docs page.

各ページについて

    density = (本文中の [text](url) リンク数) / 本文字数 * 1000

を計算し、極端に低い / 高いページを informational に report する。

* 低密度 (< 2 links / 1000 chars): 関連リンクが薄く、孤立気味のページ
* 高密度 (> 30 links / 1000 chars): リンク過多。glossary 自動注入の
  やりすぎや、ナビゲーション専用ページ等が紛れている可能性

本文の前処理:

* frontmatter (``---`` で挟まれた YAML ブロック) を除外
* HTML コメント ``<!-- ... -->`` を除外 (evidence 等)
* フェンス付きコードブロック ``` ``` / ``~~~`` を除外
* インラインコードスパン `` `...` `` を除外
* 残った本文中の ``[text](url)`` リンクを 1 件としてカウント
  (画像 ``![alt](url)`` は除外)

短いページ (本文 < 500 chars) は安定して測れないため評価対象外。

``meta/link-density-exceptions.json`` に
``{"exceptions": ["docs/path/to/page.md", ...]}`` を書くと個別除外できる。

Usage:
    python3 meta/scripts/check_link_density.py             # TSV を stdout
    python3 meta/scripts/check_link_density.py --report    # Markdown table
    python3 meta/scripts/check_link_density.py --check     # CI informational

Exit codes:
    0  always (informational)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
EXCEPTIONS = REPO_ROOT / "meta" / "link-density-exceptions.json"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Match inline [text](target) links, skip ![alt](url) images
LINK_RE = re.compile(r"(?<!\!)\[(?P<text>[^\]\n]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")

MIN_BODY_CHARS = 500
LOW_THRESHOLD = 2.0   # links / 1000 chars
HIGH_THRESHOLD = 30.0  # links / 1000 chars


def load_exceptions() -> set[str]:
    if not EXCEPTIONS.exists():
        return set()
    try:
        data = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return set(data.get("exceptions", []))


def strip_frontmatter(text: str) -> str:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text
    return text[m.end():]


def strip_code_and_comments(text: str) -> str:
    # Remove HTML comments first (may span lines, contain evidence blocks)
    text = HTML_COMMENT_RE.sub("", text)
    # Remove fenced code blocks line-by-line
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            continue
        if in_fence and stripped.startswith(fence_marker):
            in_fence = False
            continue
        if in_fence:
            continue
        out.append(line)
    body = "\n".join(out)
    # Strip inline code spans
    body = re.sub(r"`[^`\n]*`", "", body)
    return body


def measure(md: Path) -> dict[str, object] | None:
    try:
        text = md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    body = strip_code_and_comments(strip_frontmatter(text))
    body_chars = len(body)
    if body_chars < MIN_BODY_CHARS:
        return None
    link_count = sum(1 for _ in LINK_RE.finditer(body))
    density = link_count / body_chars * 1000.0
    return {
        "path": str(md.relative_to(REPO_ROOT)),
        "body_chars": body_chars,
        "link_count": link_count,
        "density": density,
    }


def collect() -> tuple[list[dict[str, object]], list[dict[str, object]], int]:
    """Return (low, high, total_evaluated)."""
    exceptions = load_exceptions()
    low: list[dict[str, object]] = []
    high: list[dict[str, object]] = []
    total = 0
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(md.relative_to(REPO_ROOT))
        if rel in exceptions:
            continue
        row = measure(md)
        if row is None:
            continue
        total += 1
        if row["density"] < LOW_THRESHOLD:
            low.append(row)
        elif row["density"] > HIGH_THRESHOLD:
            high.append(row)
    low.sort(key=lambda r: r["density"])
    high.sort(key=lambda r: r["density"], reverse=True)
    return low, high, total


def render_tsv(low: list[dict[str, object]], high: list[dict[str, object]]) -> str:
    lines = ["bucket\tpath\tbody_chars\tlink_count\tdensity_per_1k"]
    for r in low:
        lines.append(
            f"low\t{r['path']}\t{r['body_chars']}\t{r['link_count']}\t{r['density']:.2f}"
        )
    for r in high:
        lines.append(
            f"high\t{r['path']}\t{r['body_chars']}\t{r['link_count']}\t{r['density']:.2f}"
        )
    return "\n".join(lines)


def render_report(low: list[dict[str, object]], high: list[dict[str, object]], total: int) -> str:
    lines: list[str] = []
    lines.append("# link-density report")
    lines.append("")
    lines.append(
        f"Evaluated **{total}** pages (body >= {MIN_BODY_CHARS} chars). "
        f"Low threshold: < {LOW_THRESHOLD}/1k chars. "
        f"High threshold: > {HIGH_THRESHOLD}/1k chars."
    )
    lines.append("")
    lines.append(f"- low-density pages: **{len(low)}**")
    lines.append(f"- high-density pages: **{len(high)}**")
    lines.append("")
    lines.append("## Low-density pages")
    lines.append("")
    lines.append(
        "関連リンクが薄く、孤立気味の可能性。Related links / Topics へのリンク追加候補。"
    )
    lines.append("")
    if low:
        lines.append("| path | body_chars | links | density (/1k) |")
        lines.append("|------|-----------:|------:|--------------:|")
        for r in low:
            lines.append(
                f"| `{r['path']}` | {r['body_chars']} | {r['link_count']} | {r['density']:.2f} |"
            )
    else:
        lines.append("_(none)_")
    lines.append("")
    lines.append("## High-density pages")
    lines.append("")
    lines.append(
        "リンク過多。Glossary 自動注入のやりすぎ、ナビ専用ページ、"
        "リスト過密などの可能性。"
    )
    lines.append("")
    if high:
        lines.append("| path | body_chars | links | density (/1k) |")
        lines.append("|------|-----------:|------:|--------------:|")
        for r in high:
            lines.append(
                f"| `{r['path']}` | {r['body_chars']} | {r['link_count']} | {r['density']:.2f} |"
            )
    else:
        lines.append("_(none)_")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI informational モード。件数を stderr に出して 0 で終了する。",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Markdown 形式の詳細レポートを stdout に出す。",
    )
    args = parser.parse_args()

    low, high, total = collect()

    if args.check:
        print(
            f"[link-density] evaluated {total} pages: "
            f"{len(low)} low-density (< {LOW_THRESHOLD}/1k), "
            f"{len(high)} high-density (> {HIGH_THRESHOLD}/1k) (informational)",
            file=sys.stderr,
        )
        return 0

    if args.report:
        print(render_report(low, high, total))
        return 0

    print(render_tsv(low, high))
    return 0


if __name__ == "__main__":
    sys.exit(main())
