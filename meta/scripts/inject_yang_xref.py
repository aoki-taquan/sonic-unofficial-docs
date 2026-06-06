#!/usr/bin/env python3
"""Inject a `## 関連ページ` cross-link block into each YANG reference page.

For every ``docs/reference/yang/<module>.md`` (excluding ``index.md``):

1. Parse the frontmatter; read ``related.config_db`` and ``related.cli`` to
   render direct links to the matching CONFIG_DB and CLI reference pages.
2. Invert ``meta/hld-yang-map.json`` to find HLD/runbook pages that list this
   module, and scan ``docs/topics/*/index.md`` for textual references to the
   module name to surface relevant Topics chapters.
3. Insert a managed block delimited by ``<!-- yang-xref -->`` /
   ``<!-- /yang-xref -->`` immediately after the H1 (and the optional
   ``<!-- yang-mermaid -->`` block) so it sits high on the page.

Skip rules:
- A page that already has a top-level ``## 関連ページ`` heading (not inside the
  managed block) is left untouched. This honours hand-authored content.
- A page whose computed block would be empty (no targets) is skipped.

Modes:
  (default)  Rewrite drifted files in place. Prints summary. Exit 0.
  --check    Report drift; exit 1 if any file would change. No writes.

The script is idempotent: running it twice with no source changes produces
zero edits.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
YANG_DIR = DOCS / "reference" / "yang"
CDB_DIR = DOCS / "reference" / "config-db"
CLI_DIR = DOCS / "reference" / "cli"
TOPICS_DIR = DOCS / "topics"
HLD_YANG_MAP = ROOT / "meta" / "hld-yang-map.json"

OPEN_MARKER = "<!-- yang-xref -->"
CLOSE_MARKER = "<!-- /yang-xref -->"

# Match `## 関連ページ` heading (with optional trailing whitespace), but NOT
# inside the managed marker — we use this as the "user already wrote one" gate.
RELATED_H2_RE = re.compile(r"^## 関連ページ\s*$", re.MULTILINE)


def split_fm(text: str) -> tuple[dict | None, str, str]:
    """Return (frontmatter_dict, fm_block_including_fences, body)."""
    if not text.startswith("---\n"):
        return None, "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, "", text
    fm_text = text[4:end]
    body = text[end + 5 :]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None, "", text
    return fm, text[: end + 5], body


def cdb_slug(name: str) -> str:
    """`BGP_GLOBALS_AF` -> `bgp-globals-af`."""
    return name.lower().replace("_", "-")


def resolve_cdb_slug(name: str) -> str | None:
    """Resolve a CONFIG_DB table name to an existing slug under ``CDB_DIR``.

    Mirrors the trailing-segment fallback used by ``gen_ref_triangle.py`` so
    sub-tables that are documented inside a parent page (e.g. ``SNMP_COMMUNITY``
    / ``SNMP_USER`` → ``snmp.md``) still resolve to a real link target instead
    of being silently dropped from the auto-generated xref block.
    """
    base = cdb_slug(name)
    parts = base.split("-")
    while parts:
        candidate = "-".join(parts)
        if candidate and (CDB_DIR / f"{candidate}.md").exists():
            return candidate
        parts.pop()
    return None


def cli_slug(name: str) -> str:
    """`config bgp bbr` -> `config-bgp-bbr`."""
    return re.sub(r"\s+", "-", name.strip().lower())


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
    body_start = fm_match.end() if fm_match else 0
    for line in text[body_start:].splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return md_path.stem


def load_yang_to_hld() -> dict[str, list[str]]:
    """Invert hld-yang-map.json -> {module: [hld_rel_path, ...]}."""
    raw = json.loads(HLD_YANG_MAP.read_text())
    inv: dict[str, list[str]] = {}
    for rel_path, modules in raw.items():
        if rel_path.startswith("_"):
            continue
        for mod in modules:
            inv.setdefault(mod, []).append(rel_path)
    for v in inv.values():
        v.sort()
    return inv


def load_yang_to_topics() -> dict[str, list[Path]]:
    """For every topic chapter index, list yang modules mentioned in its
    ``index.md`` body. Returns inverse mapping {module: [index_path, ...]}."""
    inv: dict[str, list[Path]] = {}
    for chapter_dir in sorted(TOPICS_DIR.iterdir()):
        if not chapter_dir.is_dir():
            continue
        idx = chapter_dir / "index.md"
        if not idx.exists():
            continue
        text = idx.read_text(encoding="utf-8", errors="ignore")
        # Strip frontmatter.
        m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
        body = text[m.end():] if m else text
        # Collect sonic-* module-like tokens.
        for mod in set(re.findall(r"\bsonic-[a-z0-9_-]+", body)):
            inv.setdefault(mod, []).append(idx)
    for v in inv.values():
        v.sort()
    return inv


def render_block(module: str, fm: dict, yang_to_hld: dict[str, list[str]],
                 yang_to_topics: dict[str, list[Path]]) -> str | None:
    related = (fm.get("related") or {}) if isinstance(fm.get("related"), dict) else {}
    cdb_names = list(related.get("config_db") or [])
    cli_names = list(related.get("cli") or [])

    cdb_links: list[tuple[str, str]] = []
    seen_cdb_names: set[str] = set()
    for name in cdb_names:
        name_s = str(name)
        if name_s in seen_cdb_names:
            continue
        slug = resolve_cdb_slug(name_s)
        if not slug:
            continue
        seen_cdb_names.add(name_s)
        cdb_links.append((name_s, f"../config-db/{slug}.md"))

    cli_links: list[tuple[str, str]] = []
    for name in cli_names:
        slug = cli_slug(str(name))
        target = CLI_DIR / f"{slug}.md"
        if target.exists():
            cli_links.append((str(name), f"../cli/{slug}.md"))

    hld_links: list[tuple[str, str]] = []
    for rel in yang_to_hld.get(module, []):
        target = DOCS / rel
        if not target.exists():
            continue
        title = page_title(target)
        # Link from docs/reference/yang/X.md to docs/<rel>.
        hld_links.append((title, "../../" + rel))

    topic_links: list[tuple[str, str]] = []
    for idx in yang_to_topics.get(module, []):
        title = page_title(idx)
        rel = idx.relative_to(DOCS).as_posix()
        topic_links.append((title, "../../" + rel))

    if not (cdb_links or cli_links or hld_links or topic_links):
        return None

    lines = [
        "## 関連ページ",
        "",
        OPEN_MARKER,
        "",
        "本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。",
        "",
    ]
    if cdb_links:
        lines.append("### 対応 CONFIG_DB")
        lines.append("")
        for name, href in cdb_links:
            lines.append(f"- [`{name}`]({href})")
        lines.append("")
    if cli_links:
        lines.append("### 関連 CLI")
        lines.append("")
        for name, href in cli_links:
            lines.append(f"- [`{name}`]({href})")
        lines.append("")
    if hld_links:
        lines.append("### 関連 HLD")
        lines.append("")
        for title, href in hld_links:
            lines.append(f"- [{title}]({href})")
        lines.append("")
    if topic_links:
        lines.append("### 関連 Topics")
        lines.append("")
        for title, href in topic_links:
            lines.append(f"- [{title}]({href})")
        lines.append("")
    lines.append(CLOSE_MARKER)
    return "\n".join(lines) + "\n"


def strip_managed(body: str) -> str:
    """Remove any existing managed block (and its `## 関連ページ` header)."""
    pat = re.compile(
        r"\n*## 関連ページ\s*\n+"
        + re.escape(OPEN_MARKER)
        + r".*?"
        + re.escape(CLOSE_MARKER)
        + r"\n?",
        re.DOTALL,
    )
    new_body, n = pat.subn("\n", body)
    if n:
        return new_body
    pat2 = re.compile(
        re.escape(OPEN_MARKER) + r".*?" + re.escape(CLOSE_MARKER) + r"\n?",
        re.DOTALL,
    )
    return pat2.sub("", body)


def has_hand_authored_section(body: str) -> bool:
    """Return True if the page has a `## 関連ページ` heading that is NOT part
    of the managed (marker-delimited) block."""
    cleaned = strip_managed(body)
    return bool(RELATED_H2_RE.search(cleaned))


def find_insertion_point(body: str) -> int:
    """Return index at which to inject the block.

    Preferred: just after the closing ``<!-- /yang-mermaid -->`` line (with the
    trailing newline). Fallback: just before the first ``## `` heading.
    Last resort: end of body.
    """
    m = re.search(r"<!-- /yang-mermaid -->\s*\n", body)
    if m:
        return m.end()
    m = re.search(r"^## ", body, re.MULTILINE)
    if m:
        return m.start()
    return len(body)


def compute_new_text(path: Path, yang_to_hld, yang_to_topics) -> str | None:
    text = path.read_text(encoding="utf-8")
    fm, fm_block, body = split_fm(text)
    if fm is None:
        return None
    module = path.stem  # filename matches module name

    # If a hand-authored `## 関連ページ` already exists (not ours), skip.
    if has_hand_authored_section(body):
        return None

    block = render_block(module, fm, yang_to_hld, yang_to_topics)
    if not block:
        return None

    # Remove any previous managed block before re-inserting.
    cleaned = strip_managed(body)
    insert_at = find_insertion_point(cleaned)
    # Ensure exactly one blank line separator on both sides.
    before = cleaned[:insert_at].rstrip("\n") + "\n\n"
    after = cleaned[insert_at:].lstrip("\n")
    new_body = before + block + "\n" + after
    # Normalize trailing whitespace: keep single final newline.
    new_body = new_body.rstrip() + "\n"
    return fm_block + new_body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if any drift")
    args = ap.parse_args()

    yang_to_hld = load_yang_to_hld()
    yang_to_topics = load_yang_to_topics()

    pages = sorted(p for p in YANG_DIR.glob("*.md") if p.name != "index.md")
    drift: list[Path] = []
    updated = 0
    skipped_hand = 0
    skipped_empty = 0

    for p in pages:
        new_text = compute_new_text(p, yang_to_hld, yang_to_topics)
        if new_text is None:
            # Distinguish skip reasons for the summary.
            original = p.read_text(encoding="utf-8")
            _, _, body = split_fm(original)
            if has_hand_authored_section(body):
                skipped_hand += 1
            else:
                skipped_empty += 1
            continue
        original = p.read_text(encoding="utf-8")
        if new_text == original:
            continue
        drift.append(p)
        if not args.check:
            p.write_text(new_text, encoding="utf-8")
            updated += 1

    if args.check:
        if drift:
            sys.stderr.write(
                f"drift: {len(drift)} yang page(s) need yang-xref injection. "
                f"Run `python3 meta/scripts/inject_yang_xref.py`.\n"
            )
            for p in drift:
                sys.stderr.write(f"  - {p.relative_to(ROOT)}\n")
            return 1
        return 0

    print(
        f"yang-xref: updated={updated} skipped_hand_authored={skipped_hand} "
        f"skipped_no_targets={skipped_empty} total={len(pages)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
