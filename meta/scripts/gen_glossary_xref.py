#!/usr/bin/env python3
"""Glossary reverse-index generator.

Reads `docs/reference/glossary.md` and:

1. Ensures every term H3 heading (`### <Term>`) carries a stable anchor of the
   form ``{#term-<slug>}``. Existing anchors are preserved.
2. Scans `docs/**/*.md` (excluding the glossary itself) and builds a reverse
   index: for each term, which pages mention it in their body text.
3. Rewrites the managed block delimited by ``<!-- glossary-xref -->`` ...
   ``<!-- /glossary-xref -->`` at the end of the glossary with a "用語別 逆引き
   索引" section, listing up to 5 pages per term.

Modes:
  (default)  Rewrite drifted files in place. Exit 0.
  --check    Report drift; exit 1 if any file would change. No writes.

Notes:
- Term matching uses simple case-sensitive substring on body text (frontmatter
  excluded). The English/abbreviation form (the heading text itself) is used.
- The glossary page is skipped to avoid self-references.
- Only the top 5 pages (sorted by mention count desc, then path asc) are kept.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
GLOSSARY = DOCS / "reference" / "glossary.md"
OPEN_MARKER = "<!-- glossary-xref -->"
CLOSE_MARKER = "<!-- /glossary-xref -->"
MAX_PAGES_PER_TERM = 5

# Match `### Term` or `### Term {#anchor}` (allowing trailing whitespace).
HEADING_RE = re.compile(r"^(###\s+)(.+?)(\s*\{#([^}]+)\})?\s*$")


def slugify_term(term: str) -> str:
    """Produce a stable anchor slug from a heading text.

    Strategy: lowercase, keep ASCII alphanumerics and ``-``/``_``/``.``, replace
    other separators (``/``, whitespace) with ``-``. Collapse repeats. Always
    prefix with ``term-`` to avoid clashes with auto-generated heading IDs.
    """
    s = term.strip().lower()
    # Replace separators with `-`.
    s = re.sub(r"[\s/]+", "-", s)
    # Drop characters that aren't safe.
    s = re.sub(r"[^a-z0-9._-]+", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        s = "x"
    return f"term-{s}"


def parse_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block_including_fences, body_text)."""
    m = re.match(r"^(---\s*\n.*?\n---\s*\n)", text, re.DOTALL)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def collect_terms_and_rewrite_glossary(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Walk glossary lines, assign anchors where missing.

    Returns the rewritten text and a list of (term, anchor) pairs in document
    order. Anchor assignment is deterministic and stable for a given term.
    """
    fm, body = parse_frontmatter(text)
    out_lines: list[str] = []
    terms: list[tuple[str, str]] = []
    used_anchors: set[str] = set()

    # Strip the managed block before processing so it does not get re-parsed
    # as headings on subsequent runs.
    body = strip_managed_block(body)

    for line in body.splitlines():
        m = HEADING_RE.match(line)
        if m:
            prefix, term_text, _, existing_anchor = m.groups()
            if existing_anchor:
                anchor = existing_anchor
            else:
                anchor = slugify_term(term_text)
                # Ensure uniqueness across the glossary.
                base = anchor
                i = 2
                while anchor in used_anchors:
                    anchor = f"{base}-{i}"
                    i += 1
            used_anchors.add(anchor)
            terms.append((term_text.strip(), anchor))
            out_lines.append(f"{prefix}{term_text.strip()} {{#{anchor}}}")
        else:
            out_lines.append(line)

    new_body = "\n".join(out_lines)
    if not new_body.endswith("\n"):
        new_body += "\n"
    return fm + new_body, terms


def strip_managed_block(body: str) -> str:
    """Remove the managed glossary-xref block (and the preceding section header
    if it directly precedes the open marker) so it can be regenerated."""
    pattern = re.compile(
        r"\n*## 用語別 逆引き索引\s*\n+"
        + re.escape(OPEN_MARKER)
        + r".*?"
        + re.escape(CLOSE_MARKER)
        + r"\s*",
        re.DOTALL,
    )
    new_body, n = pattern.subn("\n", body)
    if n:
        return new_body
    # Fallback: strip just the marker block if header was missing.
    pattern2 = re.compile(
        re.escape(OPEN_MARKER) + r".*?" + re.escape(CLOSE_MARKER) + r"\s*",
        re.DOTALL,
    )
    return pattern2.sub("", body)


# ---------------------------------------------------------------------------
# Reverse index
# ---------------------------------------------------------------------------

def page_title(md_path: Path) -> str:
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return md_path.stem
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    # Fall back to first H1.
    body_start = fm_match.end() if fm_match else 0
    for line in text[body_start:].splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return md_path.stem


def page_body(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    fm_match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    return text[fm_match.end():] if fm_match else text


def build_reverse_index(terms: list[tuple[str, str]]) -> dict[str, list[tuple[Path, int]]]:
    """For each term, return list of (path, mention_count) sorted by count desc, path asc."""
    pages: list[tuple[Path, str]] = []
    for p in sorted(DOCS.rglob("*.md"), key=lambda x: x.relative_to(DOCS).as_posix()):
        if p == GLOSSARY:
            continue
        pages.append((p, page_body(p)))

    index: dict[str, list[tuple[Path, int]]] = {}
    for term, _anchor in terms:
        # Skip extremely short or generic terms (single character) just in case.
        if len(term) < 2:
            index[term] = []
            continue
        hits: list[tuple[Path, int]] = []
        for path, body in pages:
            count = body.count(term)
            if count:
                hits.append((path, count))
        hits.sort(key=lambda x: (-x[1], str(x[0].relative_to(DOCS))))
        index[term] = hits[:MAX_PAGES_PER_TERM]
    return index


def render_block(terms: list[tuple[str, str]], index: dict[str, list[tuple[Path, int]]]) -> str:
    lines = [
        "## 用語別 逆引き索引",
        "",
        OPEN_MARKER,
        "",
        "本ページの各用語が、ドキュメント内のどのページで言及されているかをまとめた逆引き索引です（言及回数の多い順に最大 "
        + str(MAX_PAGES_PER_TERM)
        + " ページ）。`gen_glossary_xref.py` により自動生成されます。",
        "",
    ]
    for term, anchor in terms:
        hits = index.get(term, [])
        if not hits:
            continue
        lines.append(f"### [{term}](#{anchor})")
        lines.append("")
        for path, count in hits:
            rel = path.relative_to(DOCS)
            # Link from docs/reference/glossary.md to docs/<rel>.
            link_target = "../" + rel.as_posix() if not str(rel).startswith("reference/") else rel.as_posix().removeprefix("reference/")
            title = page_title(path)
            lines.append(f"- [{title}]({link_target}) ({count})")
        lines.append("")
    lines.append(CLOSE_MARKER)
    lines.append("")
    return "\n".join(lines)


def compute_new_glossary(text: str) -> str:
    rewritten, terms = collect_terms_and_rewrite_glossary(text)
    fm, body = parse_frontmatter(rewritten)
    # Ensure body ends with single trailing newline before appending.
    body = body.rstrip() + "\n\n"
    index = build_reverse_index(terms)
    block = render_block(terms, index)
    return fm + body + block


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if drift")
    args = ap.parse_args()

    original = GLOSSARY.read_text(encoding="utf-8")
    updated = compute_new_glossary(original)

    if updated == original:
        return 0

    if args.check:
        import difflib
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(GLOSSARY.relative_to(ROOT)) + " (committed)",
            tofile=str(GLOSSARY.relative_to(ROOT)) + " (regenerated)",
            n=2,
        )
        sys.stderr.writelines(diff)
        sys.stderr.write(
            f"\ndrift: {GLOSSARY.relative_to(ROOT)} is out of date. "
            f"Run `python3 meta/scripts/gen_glossary_xref.py` to regenerate.\n"
        )
        return 1

    GLOSSARY.write_text(updated, encoding="utf-8")
    print(f"updated: {GLOSSARY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
