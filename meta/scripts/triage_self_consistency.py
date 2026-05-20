#!/usr/bin/env python3
"""Triage suspects produced by ``check_verification_self_consistency.py`` into
three buckets so a human can decide whether each page actually needs a
verification downgrade.

Buckets:

- **A (verbatim)**: The hedging keyword appears inside a HLD-cited factual
  statement (the same line carries a ``[^N]`` footnote, and the keyword is
  describing what the HLD itself says is unimplemented / unsupported).
  These are NOT real self-inconsistencies — the page is faithfully relaying
  the HLD's wording. Safe to exclude.

- **B (legitimate)**: The page itself is hedging about a fact (e.g.
  ``HLD で明記なし、要確認`` / ``カウンタ未確認`` without a citation, or
  parenthetical ``（... 要確認）``). These pages should be reviewed and
  likely downgraded from ``code-verified`` to ``partial`` or have the hedge
  removed.

- **C (ambiguous)**: Anything that doesn't cleanly land in A or B.
  Needs human eyes.

Not wired into CI; analysis-only.

Usage:
    python3 meta/scripts/triage_self_consistency.py
    python3 meta/scripts/triage_self_consistency.py --out meta/triage-self-consistency.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "meta" / "scripts"))

from check_verification_self_consistency import (  # noqa: E402
    DOCS_DIR,
    KEYWORD_PATTERNS,
    SUSPECT_VERIFICATIONS,
    load_exceptions,
    parse_frontmatter,
    strip_noise,
)

FOOTNOTE_REF_RE = re.compile(r"\[\^[^\]]+\]")
# Phrases the page itself uses to flag its own uncertainty.
HEDGE_MARKERS = [
    "明記なし",
    "記載なし",
    "情報なし",
    "ソースなし",
    "裏取りできず",
    "確認できず",
    "確認できていない",
    "確認できない",
    "不明",
    "TBD",
    "未調査",
    "要追跡",
    "要確認",
]


def classify_line(line: str, keyword: str) -> str:
    """Return 'A', 'B', or 'C' for a single line containing ``keyword``."""
    has_citation = bool(FOOTNOTE_REF_RE.search(line))
    # Strip footnote refs to inspect "naked" prose hedging.
    naked = FOOTNOTE_REF_RE.sub("", line)

    # B signals: explicit page-author hedging next to the keyword.
    hedge_phrases = ("明記なし", "記載なし", "情報なし", "ソースなし",
                     "裏取りできず", "確認できず", "確認できていない",
                     "確認できない", "不明")
    if any(p in naked for p in hedge_phrases):
        return "B"

    # Parenthetical hedge: e.g. "（HLDで明記なし、要確認）" or "(... TBD)".
    paren_re = re.compile(r"[（(][^（(）)]*" + re.escape(keyword) + r"[^（(）)]*[)）]")
    if paren_re.search(naked):
        # If the parenthetical also lacks a citation -> page-author hedge.
        return "B"

    # "要確認" / "未確認" / "要追跡" without a footnote ref nearby = the page
    # is itself flagging that this fact is not verified.
    if keyword in {"要確認", "未確認", "要追跡", "未調査"} and not has_citation:
        return "B"

    # TBD inside a description / heading without citation -> typically B.
    if keyword == "TBD" and not has_citation:
        return "B"

    # If the keyword sits adjacent to a footnote citation, treat as a
    # HLD-quoted factual statement (verbatim).
    if has_citation:
        # Look for "<keyword>[^N]" pattern or "[^N]" within 8 chars of keyword.
        kw_idx = line.find(keyword)
        for m in FOOTNOTE_REF_RE.finditer(line):
            # Adjacency: the citation comes shortly after the keyword.
            dist = m.start() - (kw_idx + len(keyword))
            if 0 <= dist <= 40:
                return "A"
            # Or keyword is inside a cited bullet (footnote at end of line).
        # Citation present somewhere on the line but not adjacent -> A by default
        # (the line is a cited factual claim, keyword describes HLD content).
        return "A"

    return "C"


def classify_page(path: Path, hits: list[tuple[str, int]]) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    cleaned = strip_noise(body)
    lines = cleaned.splitlines()

    per_hit_classes: list[str] = []
    examples: list[tuple[str, str, str]] = []  # (cls, keyword, line snippet)

    for keyword, _count in hits:
        pat = next(p for k, p in KEYWORD_PATTERNS if k == keyword)
        for line in lines:
            if pat.search(line):
                cls = classify_line(line, keyword)
                per_hit_classes.append(cls)
                snippet = line.strip()
                if len(snippet) > 160:
                    snippet = snippet[:157] + "..."
                examples.append((cls, keyword, snippet))

    # Page-level bucket: priority B > C > A.
    if "B" in per_hit_classes:
        page_class = "B"
    elif "C" in per_hit_classes:
        page_class = "C"
    else:
        page_class = "A"

    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "verification": fm.get("verification", ""),
        "hits": hits,
        "page_class": page_class,
        "examples": examples,
    }


def collect_suspects() -> list[dict[str, object]]:
    """Reproduce ``check_verification_self_consistency.collect`` then enrich
    each entry with a triage class."""
    from check_verification_self_consistency import find_keywords
    exceptions = load_exceptions()
    out: list[dict[str, object]] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(md.relative_to(REPO_ROOT))
        if rel in exceptions:
            continue
        text = md.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if fm.get("verification", "") not in SUSPECT_VERIFICATIONS:
            continue
        hits = find_keywords(body)
        if not hits:
            continue
        out.append(classify_page(md, hits))
    return out


def render(suspects: list[dict[str, object]]) -> str:
    buckets = {"A": [], "B": [], "C": []}
    for s in suspects:
        buckets[s["page_class"]].append(s)  # type: ignore[index]

    lines = [
        "# verification self-consistency triage",
        "",
        "`check_verification_self_consistency.py` で検出された "
        f"{len(suspects)} 件の suspect を 3 分類した。",
        "",
        "| Class | 件数 | 意味 |",
        "|---|---|---|",
        f"| A (verbatim) | {len(buckets['A'])} | HLD 引用として `未実装` `未対応` `TBD` 等が本文に残っているだけ。実 issue ではない。除外候補。 |",
        f"| B (legitimate) | {len(buckets['B'])} | 本文の主張として `要確認` `未確認` 等を肯定的に使っている。`verification` を `partial` 等へ降格すべき。 |",
        f"| C (ambiguous) | {len(buckets['C'])} | 上記いずれにも当てはまらず、人間レビューが必要。 |",
        "",
        "分類ルールは `meta/scripts/triage_self_consistency.py` 参照。",
        "",
    ]

    for cls in ("B", "C", "A"):
        title = {
            "A": "A. verbatim (HLD 引用)",
            "B": "B. legitimate (本文の主張で未確認/未実装)",
            "C": "C. ambiguous",
        }[cls]
        items = buckets[cls]
        lines.append(f"## {title} — {len(items)} 件")
        lines.append("")
        if not items:
            lines.append("該当なし。")
            lines.append("")
            continue
        lines.append("| Path | verification | hits | 例 |")
        lines.append("|---|---|---|---|")
        for s in items:
            hits_str = ", ".join(f"{k}×{n}" for k, n in s["hits"])  # type: ignore[misc]
            # Pick first example matching this class (or the page class).
            example = ""
            for ex_cls, kw, snip in s["examples"]:  # type: ignore[misc]
                if ex_cls == cls:
                    example = f"`{kw}`: {snip}"
                    break
            example = example.replace("|", "\\|")
            lines.append(
                f"| `{s['path']}` | {s['verification']} | {hits_str} | {example} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "meta" / "triage-self-consistency.md",
        help="output markdown path (default: meta/triage-self-consistency.md)",
    )
    ap.add_argument(
        "--stdout",
        action="store_true",
        help="print to stdout instead of writing to --out",
    )
    args = ap.parse_args()

    suspects = collect_suspects()
    report = render(suspects)
    if args.stdout:
        print(report)
    else:
        args.out.write_text(report, encoding="utf-8")
        a = sum(1 for s in suspects if s["page_class"] == "A")
        b = sum(1 for s in suspects if s["page_class"] == "B")
        c = sum(1 for s in suspects if s["page_class"] == "C")
        print(f"wrote {args.out} (total={len(suspects)} A={a} B={b} C={c})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
