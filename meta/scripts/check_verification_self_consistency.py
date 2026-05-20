#!/usr/bin/env python3
"""Detect docs/**/*.md pages that claim ``verification: code-verified`` (or
``runbook-verified``) yet still contain hedging keywords like ``未実装`` /
``TBD`` / ``未確認`` / ``要確認`` / ``未調査`` etc. in their prose.

Such pages are self-inconsistent: 裏取り済みを自称しているのに本文に「未確認」
等の文字列が残っていれば、frontmatter か本文のどちらかが嘘をついている。

Usage:
    python3 meta/scripts/check_verification_self_consistency.py --report
    python3 meta/scripts/check_verification_self_consistency.py --check
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
EXCEPTIONS_FILE = REPO_ROOT / "meta" / "verification-self-consistency-exceptions.json"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FENCED_CODE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# 検知対象キーワード (regex)。日本語 + TBD など。
KEYWORD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("未実装", re.compile(r"未実装")),
    ("TBD", re.compile(r"\bTBD\b")),
    ("未確認", re.compile(r"未確認")),
    ("要確認", re.compile(r"要確認")),
    ("未調査", re.compile(r"未調査")),
    ("要追跡", re.compile(r"要追跡")),
    ("未取り込み", re.compile(r"未取り込み")),
    ("未対応", re.compile(r"未対応")),
    ("まだ実装されていない", re.compile(r"(?:まだ|未だ)実装されていない")),
]

SUSPECT_VERIFICATIONS = {"code-verified", "runbook-verified"}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, body)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    body = text[m.end():]
    return fm, body


def strip_noise(body: str) -> str:
    """Remove fenced code blocks / inline code / HTML comments from the body."""
    body = HTML_COMMENT_RE.sub("", body)
    body = FENCED_CODE_RE.sub("", body)
    body = INLINE_CODE_RE.sub("", body)
    return body


def load_exceptions() -> set[str]:
    if not EXCEPTIONS_FILE.exists():
        return set()
    data = json.loads(EXCEPTIONS_FILE.read_text(encoding="utf-8"))
    return set(data.get("exceptions", []))


def find_keywords(body: str) -> list[tuple[str, int]]:
    """Return list of (keyword_label, count) hits."""
    cleaned = strip_noise(body)
    hits: list[tuple[str, int]] = []
    for label, pat in KEYWORD_PATTERNS:
        matches = pat.findall(cleaned)
        if matches:
            hits.append((label, len(matches)))
    return hits


def collect() -> list[dict[str, object]]:
    exceptions = load_exceptions()
    suspects: list[dict[str, object]] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(md.relative_to(REPO_ROOT))
        if rel in exceptions:
            continue
        text = md.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        verification = fm.get("verification", "")
        if verification not in SUSPECT_VERIFICATIONS:
            continue
        hits = find_keywords(body)
        if not hits:
            continue
        suspects.append(
            {
                "path": rel,
                "verification": verification,
                "hits": hits,
            }
        )
    return suspects


def render_report(suspects: list[dict[str, object]]) -> str:
    if not suspects:
        return "No suspects found.\n"
    lines = ["# verification self-consistency report\n",
             f"Total suspects: {len(suspects)}\n",
             "| Path | verification | hits |",
             "|---|---|---|"]
    for s in suspects:
        hits_str = ", ".join(f"{k}×{n}" for k, n in s["hits"])  # type: ignore[misc]
        lines.append(f"| `{s['path']}` | {s['verification']} | {hits_str} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any suspect found (default: exit 0)")
    ap.add_argument("--report", action="store_true",
                    help="print a markdown table of suspects to stdout")
    args = ap.parse_args()

    suspects = collect()

    if args.report:
        print(render_report(suspects))
    else:
        print(f"suspects: {len(suspects)}")
        for s in suspects[:20]:
            hits_str = ", ".join(f"{k}×{n}" for k, n in s["hits"])  # type: ignore[misc]
            print(f"  {s['path']} [{s['verification']}] {hits_str}")
        if len(suspects) > 20:
            print(f"  ... and {len(suspects) - 20} more")

    if args.check and suspects:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
