#!/usr/bin/env python3
"""Generate mini data-flow mermaid blocks for YANG reference pages.

Each `docs/reference/yang/<slug>.md` page may reference one or more
CONFIG_DB tables via its frontmatter `related.config_db` field. For pages
that have at least one such table present in
`docs/reference/config-db-orch-map.md`, this script injects a
`<!-- yang-mermaid -->` ... `<!-- /yang-mermaid -->` block visualising:

    YANG module --> CONFIG_DB table(s) --> daemon/orch

Usage:
    python3 meta/scripts/gen_yang_mermaid.py        # write
    python3 meta/scripts/gen_yang_mermaid.py --check  # diff only (idempotent)
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / "docs" / "reference" / "config-db-orch-map.md"
PAGES_DIR = ROOT / "docs" / "reference" / "yang"

BEGIN_TAG = "<!-- yang-mermaid -->"
END_TAG = "<!-- /yang-mermaid -->"

ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
BLOCK_RE = re.compile(
    re.escape(BEGIN_TAG) + r".*?" + re.escape(END_TAG) + r"\n?",
    re.DOTALL,
)


def parse_map() -> dict[str, str]:
    """Parse orch-map rows. Returns dict TABLE_NAME -> daemon (first wins)."""
    result: dict[str, str] = {}
    text = MAP_FILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        table, subscriber = m.group(1), m.group(2)
        if table in ("CONFIG_DB", "CONFIG_DB テーブル"):
            continue
        daemon = extract_daemon(subscriber)
        if not daemon:
            continue
        # first wins, so primary daemon is preserved
        result.setdefault(table, daemon)
    return result


def extract_daemon(subscriber: str) -> Optional[str]:
    m = re.search(r"`([A-Za-z][A-Za-z0-9_]*)`", subscriber)
    if m:
        return m.group(1)
    m = re.search(r"([A-Z][A-Za-z0-9]*Orch)", subscriber)
    if m:
        return m.group(1)
    return None


def get_config_db_tables(text: str) -> list[str]:
    """Extract `related.config_db` table list from frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return []
    fm = m.group(1)
    # inline form: `config_db: [A, B, C]`
    inline = re.search(r"\n\s*config_db:\s*\[(.*?)\]", fm)
    if inline:
        raw = inline.group(1).strip()
        if not raw:
            return []
        return [t.strip().strip("`\"'") for t in raw.split(",") if t.strip()]
    # block form
    block = re.search(r"\n\s*config_db:\s*\n((?:\s+- .+\n)+)", fm)
    if block:
        out = []
        for ln in block.group(1).splitlines():
            mm = re.match(r"\s+-\s+(.+)$", ln)
            if mm:
                out.append(mm.group(1).strip().strip("`\"'"))
        return out
    return []


def get_module_name(text: str, fallback: str) -> str:
    """Pull module name from frontmatter title or fallback to slug."""
    m = FRONTMATTER_RE.match(text)
    if m:
        t = re.search(r"\ntitle:\s*(.+)", m.group(1))
        if t:
            name = t.group(1).strip().strip("\"'")
            # strip trailing " YANG"
            name = re.sub(r"\s+YANG\s*$", "", name)
            return name
    return fallback


def build_mermaid(module: str, tables: list[tuple[str, Optional[str]]]) -> str:
    """tables: list of (table_name, daemon_or_None)."""
    lines = ["```mermaid", "flowchart LR"]
    lines.append(f'  Y["{module}"]')
    daemon_nodes: dict[str, str] = {}
    for i, (table, daemon) in enumerate(tables, 1):
        cid = f"C{i}"
        lines.append(f'  {cid}[("CONFIG_DB<br/>{table}")]')
        lines.append(f"  Y --> {cid}")
        if daemon:
            if daemon not in daemon_nodes:
                did = f"D{len(daemon_nodes) + 1}"
                daemon_nodes[daemon] = did
                lines.append(f'  {did}["{daemon}"]')
            lines.append(f"  {cid} --> {daemon_nodes[daemon]}")
    lines.append("```")
    return "\n".join(lines)


def render_block(module: str, tables: list[tuple[str, Optional[str]]]) -> str:
    mermaid = build_mermaid(module, tables)
    return (
        f"{BEGIN_TAG}\n"
        f"### データフロー (自動生成)\n\n"
        f"{mermaid}\n\n"
        f"!!! note \"凡例\"\n"
        f"    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを "
        f"`docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。\n"
        f"{END_TAG}"
    )


def insert_block(text: str, block: str) -> str:
    """Replace existing block or insert after `## 動作仕様` (preferred) or
    `## 概要` body, or right after frontmatter as fallback.
    """
    if BEGIN_TAG in text:
        return BLOCK_RE.sub(block + "\n", text, count=1)

    m = FRONTMATTER_RE.match(text)
    insert_at = m.end() if m else 0

    # Preferred: right after `## 動作仕様` header
    dousa = re.search(r"\n## 動作仕様\n", text[insert_at:])
    if dousa:
        pos = insert_at + dousa.end()
        return text[:pos] + "\n" + block + "\n" + text[pos:]

    # Next preference: end of `## 概要` body
    gaiyou = re.search(r"\n## 概要\n", text[insert_at:])
    if gaiyou:
        start = insert_at + gaiyou.end()
        next_h2 = re.search(r"\n## ", text[start:])
        if next_h2:
            pos = start + next_h2.start()
            return text[:pos] + "\n" + block + "\n" + text[pos:]
        return text + "\n" + block + "\n"

    return text[:insert_at] + "\n" + block + "\n" + text[insert_at:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="Fail if any file would change")
    args = ap.parse_args()

    mapping = parse_map()
    print(f"[gen_yang_mermaid] parsed {len(mapping)} CONFIG_DB tables from orch-map", file=sys.stderr)

    changed = 0
    inserted = 0
    skipped_no_tables = 0
    skipped_no_mapping = 0
    drift: list[str] = []

    for page in sorted(PAGES_DIR.glob("*.md")):
        if page.stem == "index":
            continue
        text = page.read_text(encoding="utf-8")
        tables = get_config_db_tables(text)
        if not tables:
            skipped_no_tables += 1
            continue
        resolved: list[tuple[str, Optional[str]]] = []
        for t in tables:
            if t in mapping:
                resolved.append((t, mapping[t]))
        if not resolved:
            skipped_no_mapping += 1
            continue
        module = get_module_name(text, page.stem)
        block = render_block(module, resolved)
        new_text = insert_block(text, block)
        if new_text != text:
            if args.check:
                drift.append(str(page.relative_to(ROOT)))
            else:
                page.write_text(new_text, encoding="utf-8")
            changed += 1
        if BEGIN_TAG in new_text:
            inserted += 1

    print(
        f"[gen_yang_mermaid] inserted/updated: {changed} | total with block: {inserted} | "
        f"skipped (no tables): {skipped_no_tables} | skipped (no mapping): {skipped_no_mapping}",
        file=sys.stderr,
    )
    if args.check and drift:
        print("[gen_yang_mermaid] drift detected in:", file=sys.stderr)
        for p in drift:
            print(f"  - {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
