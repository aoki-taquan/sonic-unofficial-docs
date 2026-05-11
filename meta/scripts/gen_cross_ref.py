#!/usr/bin/env python3
"""Bidirectional cross-reference generator (Topics index.md -> area pages).

For each `docs/topics/<chapter>/index.md`, gather links to area pages from:

1. The `## 関連ページ` section (existing convention).
2. The frontmatter `sources:` list (entries pointing to `docs/<area>/...md`).

Then write a "## 関連 Topics" back-reference block at the end of each target
area page, between markers `<!-- topics-back-ref -->` (open) and
`<!-- /topics-back-ref -->` (close). The block is **regenerated** every run so
that slug renames, title updates, or chapter splits propagate automatically.

Legacy back-ref blocks that lack the close marker (placed at EOF) are detected
and migrated: everything from the open marker to EOF is treated as the managed
block and rewritten with both markers.

Modes:
  (default)  Rewrite drifted files in place. Exit 0.
  --check    Report drift; exit 1 if any file would change. No writes.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
TOPICS_DIR = DOCS / "topics"
OPEN_MARKER = "<!-- topics-back-ref -->"
CLOSE_MARKER = "<!-- /topics-back-ref -->"

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


# ---------------------------------------------------------------------------
# Topic chapter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter-as-dict, body)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}, text
    fm_text = m.group(1)
    body = text[m.end():]
    return _parse_simple_yaml(fm_text), body


def _parse_simple_yaml(fm_text: str) -> dict:
    """Tiny YAML subset: scalar keys and `key:` followed by `- item` lists."""
    out: dict = {}
    cur_list: list[str] | None = None
    for raw in fm_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(" ") or raw.startswith("\t"):
            s = raw.strip()
            if s.startswith("- ") and cur_list is not None:
                cur_list.append(s[2:].strip().strip('"').strip("'"))
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*)$", raw)
        if not m:
            cur_list = None
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            cur_list = []
            out[key] = cur_list
        else:
            out[key] = val.strip('"').strip("'")
            cur_list = None
    return out


def get_chapter_title(index_path: Path, fm: dict) -> str:
    title = fm.get("title")
    if isinstance(title, str) and title:
        return title
    text = index_path.read_text(encoding="utf-8")
    h1 = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1:
        return h1.group(1).strip()
    return index_path.parent.name


def extract_related_links(text: str) -> list[str]:
    """Hrefs in `## 関連ページ` section (relative)."""
    lines = text.splitlines()
    in_section = False
    section_lines: list[str] = []
    for line in lines:
        if re.match(r"^##\s+関連ページ\s*$", line):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+", line):
            break
        if in_section:
            section_lines.append(line)
    out: list[str] = []
    for line in section_lines:
        for m in LINK_RE.finditer(line):
            href = m.group(2)
            if not href.endswith(".md"):
                continue
            out.append(href)
    return out


def resolve_targets(index_path: Path, hrefs: list[str], sources: list[str]) -> set[Path]:
    """Resolve area target paths from in-page hrefs (relative to index.md)
    and from frontmatter `sources:` entries (repo-root relative).
    """
    targets: set[Path] = set()
    for href in hrefs:
        if not href.startswith("../../"):
            # only links escaping topics/ point to area pages
            continue
        target = (index_path.parent / href).resolve()
        if _is_area_page(target):
            targets.add(target)
    for src in sources:
        if not src.endswith(".md"):
            continue
        candidate = (ROOT / src).resolve()
        if _is_area_page(candidate):
            targets.add(candidate)
    return targets


def _is_area_page(p: Path) -> bool:
    if not p.exists():
        return False
    try:
        p.relative_to(DOCS)
    except ValueError:
        return False
    try:
        p.relative_to(TOPICS_DIR)
        return False  # inside topics/ — not an area page
    except ValueError:
        pass
    return p.suffix == ".md"


# ---------------------------------------------------------------------------
# Back-ref rendering
# ---------------------------------------------------------------------------

def render_block(target: Path, entries: list[tuple[str, Path]]) -> str:
    """entries: list of (chapter_title, topic_index_path)."""
    import os
    lines = [OPEN_MARKER, "## 関連 Topics", ""]
    for title, topic_index in entries:
        rel = os.path.relpath(topic_index, start=target.parent).replace(os.sep, "/")
        lines.append(f"- [Topics: {title}]({rel})")
    lines.append("")
    lines.append(CLOSE_MARKER)
    return "\n".join(lines)


def apply_block(text: str, block: str) -> str:
    """Replace or append the managed block in `text`."""
    if OPEN_MARKER in text and CLOSE_MARKER in text:
        pattern = re.compile(
            re.escape(OPEN_MARKER) + r".*?" + re.escape(CLOSE_MARKER),
            re.DOTALL,
        )
        return pattern.sub(block, text, count=1)
    if OPEN_MARKER in text:
        # legacy: open marker only, runs to EOF
        idx = text.index(OPEN_MARKER)
        before = text[:idx].rstrip() + "\n\n"
        return before + block + "\n"
    # new file: append at EOF
    tail = text if text.endswith("\n") else text + "\n"
    return tail + "\n" + block + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def collect_mapping() -> dict[Path, list[tuple[str, Path]]]:
    mapping: dict[Path, list[tuple[str, Path]]] = {}
    for index_path in sorted(TOPICS_DIR.glob("*/index.md")):
        text = index_path.read_text(encoding="utf-8")
        fm, _body = parse_frontmatter(text)
        title = get_chapter_title(index_path, fm)
        hrefs = extract_related_links(text)
        sources = fm.get("sources") or []
        if not isinstance(sources, list):
            sources = []
        targets = resolve_targets(index_path, hrefs, sources)
        for target in targets:
            entries = mapping.setdefault(target, [])
            tup = (title, index_path)
            if tup not in entries:
                entries.append(tup)
    # Stable order: sort by chapter directory name (which is 01-…, 02-…, …)
    for entries in mapping.values():
        entries.sort(key=lambda t: t[1].parent.name)
    return mapping


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="Report drift without writing; exit 1 if any drift.",
    )
    args = ap.parse_args()

    mapping = collect_mapping()

    drifted: list[Path] = []
    rewritten = 0
    unchanged = 0
    for target, entries in sorted(mapping.items()):
        current = target.read_text(encoding="utf-8")
        block = render_block(target, entries)
        new_text = apply_block(current, block)
        if new_text == current:
            unchanged += 1
            continue
        drifted.append(target)
        if not args.check:
            target.write_text(new_text, encoding="utf-8")
            rewritten += 1

    total_chapters = len(list(TOPICS_DIR.glob("*/index.md")))
    print(f"topic chapters scanned: {total_chapters}")
    print(f"unique target area pages: {len(mapping)}")
    print(f"unchanged: {unchanged}")
    if args.check:
        print(f"would-rewrite: {len(drifted)}")
        if drifted:
            print("\nDrifted files:")
            for p in drifted:
                print(f"  - {p.relative_to(ROOT)}")
            print(
                "\nRun `python3 meta/scripts/gen_cross_ref.py` to regenerate.",
                file=sys.stderr,
            )
            return 1
        return 0
    print(f"rewritten: {rewritten}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
