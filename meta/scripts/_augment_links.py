#!/usr/bin/env python3
"""One-shot helper: inject a '## 参考リンク' section listing related CLI/CDB/YANG
reference pages, into the given doc pages. Idempotent (skips files that already
contain the marker).
"""
from __future__ import annotations
import re, sys, yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CDB_DIR = DOCS / "reference" / "config-db"
CLI_DIR = DOCS / "reference" / "cli"
YANG_DIR = DOCS / "reference" / "yang"

MARKER = "<!-- augmented-links: v1 -->"
SECTION_HEADING = "## 参考リンク"

def slugify_cdb(name: str) -> list[str]:
    # CDB table names like "MUX_LINKMGR" -> "mux-linkmgr.md"
    base = name.strip().lower().replace("_", "-")
    cands = [base + ".md"]
    # Plural / singular variants
    if base.endswith("s"):
        cands.append(base[:-1] + ".md")
    else:
        cands.append(base + "s.md")
    return cands

def slugify_cli(cmd: str) -> str:
    # CLI commands like "config muxcable mode" -> filename starts with "config-muxcable"
    # The reference filenames are usually first 2 tokens joined with '-'
    parts = cmd.strip().split()
    if not parts:
        return ""
    # Try increasingly shorter prefixes
    for n in range(len(parts), 0, -1):
        candidate = "-".join(parts[:n]) + ".md"
        if (CLI_DIR / candidate).exists():
            return candidate
    return ""

def slugify_yang(mod: str) -> str:
    return mod.strip() + ".md"

def find_existing(rel_dir: Path, slug: str) -> Path | None:
    if not slug:
        return None
    p = rel_dir / slug
    return p if p.exists() else None

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

def parse_frontmatter(text: str) -> tuple[dict, int]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, 0
    try:
        return yaml.safe_load(m.group(1)) or {}, m.end()
    except Exception:
        return {}, m.end()

def doc_relpath(target: Path, doc: Path) -> str:
    # Relative path from doc to target, both under DOCS.
    import os
    return os.path.relpath(target, doc.parent).replace("\\", "/")

def augment(doc: Path, max_links: int = 5) -> int:
    text = doc.read_text(encoding="utf-8")
    if MARKER in text:
        return 0
    fm, end = parse_frontmatter(text)
    if not fm:
        return 0
    related = fm.get("related") or {}
    cdb = related.get("config_db") or []
    cli = related.get("cli") or []
    yang = related.get("yang") or []

    links: list[tuple[str, str]] = []  # (display, url)

    # Prefer CLI commands first (most actionable), then CDB, then YANG
    for cmd in cli:
        p = find_existing(CLI_DIR, slugify_cli(cmd))
        if p:
            links.append((f"`{cmd}` CLI リファレンス", doc_relpath(p, doc)))
            if len(links) >= max_links:
                break

    if len(links) < max_links:
        for tbl in cdb:
            for slug in slugify_cdb(tbl):
                p = find_existing(CDB_DIR, slug)
                if p:
                    links.append((f"`{tbl}` CONFIG_DB スキーマ", doc_relpath(p, doc)))
                    break
            if len(links) >= max_links:
                break

    if len(links) < max_links:
        for mod in yang:
            p = find_existing(YANG_DIR, slugify_yang(mod))
            if p:
                links.append((f"`{mod}` YANG モジュール", doc_relpath(p, doc)))
                if len(links) >= max_links:
                    break

    # Fallback: if reference matches are thin, top up with internal nav
    # (category index + glossary) so we hit at least 2 links.
    if len(links) < 2:
        area_idx = DOCS / fm.get("area", "") / "index.md" if fm.get("area") else None
        glossary = DOCS / "reference" / "glossary.md"
        if area_idx and area_idx.exists():
            links.append((f"{fm.get('area')} カテゴリ目次", doc_relpath(area_idx, doc)))
        if glossary.exists() and len(links) < max_links:
            links.append(("用語集 (Glossary)", doc_relpath(glossary, doc)))

    # If still nothing matched at all, skip
    if len(links) < 2:
        return 0

    # Build section
    section_lines = ["", SECTION_HEADING, "", "本ページに関連する参照ドキュメント:", ""]
    for display, url in links:
        section_lines.append(f"- [{display}]({url})")
    section_lines.append("")
    section_lines.append(MARKER)
    section_lines.append("")
    new_section = "\n".join(section_lines)

    # Insert before any next-reads:start block, otherwise append before final
    # glossary-links-injected marker, otherwise at end.
    insert_anchors = [
        "<!-- next-reads:start -->",
    ]
    inserted = False
    for anchor in insert_anchors:
        idx = text.find(anchor)
        if idx != -1:
            # find start of line for clean insertion
            line_start = text.rfind("\n", 0, idx) + 1
            text = text[:line_start] + new_section + "\n" + text[line_start:]
            inserted = True
            break
    if not inserted:
        # insert before glossary marker if present at end
        gloss_idx = text.rfind("<!-- glossary-links-injected:")
        if gloss_idx != -1:
            line_start = text.rfind("\n", 0, gloss_idx) + 1
            text = text[:line_start] + new_section + "\n" + text[line_start:]
        else:
            if not text.endswith("\n"):
                text += "\n"
            text += new_section + "\n"

    doc.write_text(text, encoding="utf-8")
    return len(links)


def main():
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        print("usage: _augment_links.py <doc.md> [...]")
        sys.exit(2)
    total_links = 0
    touched = 0
    for p in paths:
        if not p.is_absolute():
            p = ROOT / p
        n = augment(p)
        if n > 0:
            touched += 1
            total_links += n
            print(f"  +{n} links  {p.relative_to(ROOT)}")
        else:
            print(f"  skip      {p.relative_to(ROOT)}")
    print(f"done: touched={touched} files, added={total_links} links")


if __name__ == "__main__":
    main()
