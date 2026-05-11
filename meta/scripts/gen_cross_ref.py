#!/usr/bin/env python3
"""Bidirectional cross-reference generator (Topics index.md -> area pages).

For each `docs/topics/<chapter>/index.md`, extract links in the
"## 関連ページ" section that point to `../../<area>/.../<slug>.md`.
Then append a back-reference block to each target page (marker:
`<!-- topics-back-ref -->`) pointing back to the Topics chapter.

Idempotent: targets that already contain the marker are skipped.
Frontmatter is not modified.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
TOPICS_DIR = DOCS / "topics"
MARKER = "<!-- topics-back-ref -->"

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def get_chapter_title(index_path: Path) -> str:
    """Return chapter title from frontmatter `title:` field, fallback to first H1."""
    text = index_path.read_text(encoding="utf-8")
    m = re.search(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if m:
        fm = m.group(1)
        tm = re.search(r"^title:\s*(.+)$", fm, re.MULTILINE)
        if tm:
            return tm.group(1).strip().strip('"').strip("'")
    h1 = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1:
        return h1.group(1).strip()
    return index_path.parent.name


def extract_related_links(index_path: Path) -> list[tuple[str, Path]]:
    """Return list of (link_text, absolute_target_path) for links in
    the `## 関連ページ` section that target `../../<area>/...md`.
    """
    text = index_path.read_text(encoding="utf-8")
    # find section
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
    results: list[tuple[str, Path]] = []
    for line in section_lines:
        for m in LINK_RE.finditer(line):
            text_, href = m.group(1), m.group(2)
            if not href.startswith("../../"):
                continue
            if not href.endswith(".md"):
                continue
            # resolve relative to index.md's directory
            target = (index_path.parent / href).resolve()
            try:
                target.relative_to(DOCS)
            except ValueError:
                continue
            results.append((text_, target))
    return results


def relpath_from_target_to_topic(target: Path, topic_index: Path) -> str:
    """Compute markdown link from target page to topic index.md."""
    import os
    rel = os.path.relpath(topic_index, start=target.parent)
    return rel.replace(os.sep, "/")


def append_back_ref(target: Path, entries: list[tuple[str, str]]) -> bool:
    """Append a back-ref block to `target` if marker not present.

    `entries` is a list of (chapter_title, relative_link).
    Returns True if file was modified.
    """
    text = target.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    block_lines = ["", MARKER, "## 関連 Topics", ""]
    for title, rel in entries:
        block_lines.append(f"- [Topics: {title}]({rel})")
    block_lines.append("")
    new_text = text
    if not new_text.endswith("\n"):
        new_text += "\n"
    new_text += "\n".join(block_lines)
    target.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    # mapping: target_path -> list of (chapter_title, rel_link)
    mapping: dict[Path, list[tuple[str, str]]] = {}
    total_links_seen = 0
    topics_processed = 0

    for index_path in sorted(TOPICS_DIR.glob("*/index.md")):
        chapter_title = get_chapter_title(index_path)
        links = extract_related_links(index_path)
        if not links:
            continue
        topics_processed += 1
        for _text, target in links:
            if not target.exists():
                # skip dangling refs
                continue
            # skip if target is itself a topics/index.md (intra-topics handled separately)
            try:
                target.relative_to(TOPICS_DIR)
                continue
            except ValueError:
                pass
            total_links_seen += 1
            rel = relpath_from_target_to_topic(target, index_path)
            entry = (chapter_title, rel)
            mapping.setdefault(target, [])
            if entry not in mapping[target]:
                mapping[target].append(entry)

    modified = 0
    skipped = 0
    for target, entries in sorted(mapping.items()):
        if append_back_ref(target, entries):
            modified += 1
        else:
            skipped += 1

    print(f"topics chapters with 関連ページ: {topics_processed}")
    print(f"unique target pages: {len(mapping)}")
    print(f"total link occurrences: {total_links_seen}")
    print(f"back-refs added: {modified}")
    print(f"already-had-marker (skipped): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
