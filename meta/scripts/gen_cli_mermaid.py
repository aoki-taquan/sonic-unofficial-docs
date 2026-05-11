#!/usr/bin/env python3
"""Generate mini data-flow mermaid blocks for CLI reference pages.

For each `docs/reference/cli/<slug>.md` whose frontmatter declares
`related.config_db: [...]`, inject a `<!-- cli-mermaid -->` block that shows:

  config 系: CLI --> sonic-cfggen --> CONFIG_DB(table) --> daemon
  show  系: CONFIG_DB(table) --> CLI

The daemon for each table is resolved via `docs/reference/config-db-orch-map.md`
(same parser as `gen_cdb_mermaid.py`). The block is placed right before
`<!-- topics-back-ref -->` when present, otherwise before `<!-- ref-triangle:start -->`,
otherwise at end of file.

Usage:
    python3 meta/scripts/gen_cli_mermaid.py        # write
    python3 meta/scripts/gen_cli_mermaid.py --check  # diff only (drift detect)
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / "docs" / "reference" / "config-db-orch-map.md"
PAGES_DIR = ROOT / "docs" / "reference" / "cli"

BEGIN_TAG = "<!-- cli-mermaid -->"
END_TAG = "<!-- /cli-mermaid -->"

ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_map() -> dict[str, Optional[str]]:
    """Return TABLE_NAME -> daemon (first match wins)."""
    result: dict[str, Optional[str]] = {}
    text = MAP_FILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        table, subscriber, _appl, _sai = m.group(1), m.group(2), m.group(3), m.group(4)
        if table in ("CONFIG_DB", "CONFIG_DB テーブル"):
            continue
        if table in result:
            continue
        daemon = extract_daemon(subscriber)
        if daemon:
            result[table] = daemon
    return result


def extract_daemon(subscriber: str) -> Optional[str]:
    m = re.search(r"`([A-Za-z][A-Za-z0-9_]*)`", subscriber)
    if m:
        return m.group(1)
    m = re.search(r"([A-Z][A-Za-z0-9]*Orch)", subscriber)
    if m:
        return m.group(1)
    return None


def parse_frontmatter(text: str) -> dict[str, list[str]]:
    """Extract related.config_db list and related.cli list from frontmatter."""
    out: dict[str, list[str]] = {"config_db": [], "cli": []}
    m = FRONTMATTER_RE.match(text)
    if not m:
        return out
    fm = m.group(1)
    for key in ("config_db", "cli"):
        block_re = re.compile(r"\n  " + key + r":\s*\n((?:    - .+\n)+)")
        bm = block_re.search(fm)
        if not bm:
            continue
        for line in bm.group(1).splitlines():
            item = line.strip()
            if item.startswith("- "):
                out[key].append(item[2:].strip())
    return out


def slug_to_command(slug: str) -> str:
    """Best-effort CLI command name from filename slug.

    Examples:
      config-bgp        -> 'config bgp'
      show-interfaces   -> 'show interfaces'
      clear-counters    -> 'clear counters'
      reboot-fast-warm  -> 'reboot / fast-reboot / warm-reboot'
      debug-group       -> 'debug'
    """
    if slug == "reboot-fast-warm":
        return "reboot / fast-reboot / warm-reboot"
    if slug == "debug-group":
        return "debug"
    if slug == "clear":
        return "sonic-clear"
    return slug.replace("-", " ", 1) if slug.startswith(("config-", "show-", "clear-")) else slug.replace("-", " ")


def is_show_page(slug: str) -> bool:
    return slug.startswith("show-") or slug.startswith("clear")


def build_mermaid(command: str, tables_daemons: list[tuple[str, Optional[str]]], show_dir: bool) -> str:
    """Build a mini flowchart.

    For config: CLI --> SC --> CDB(table) --> DM(daemon) [one or many tables]
    For show:   CDB(table) --> CLI
    """
    lines = ["```mermaid", "flowchart LR"]
    # sanitize command label for mermaid (escape backticks/quotes minimally)
    label_cmd = command.replace('"', "'")
    lines.append(f'  CLI["{label_cmd}"]')

    if show_dir:
        # show / clear: CDB(s) --> CLI
        for i, (tbl, _dm) in enumerate(tables_daemons):
            n = f"CDB{i}"
            lines.append(f'  {n}[("CONFIG_DB<br/>{tbl}")]')
            lines.append(f"  {n} --> CLI")
    else:
        # config: CLI --> SC --> per-table CDB --> daemon
        lines.append('  SC["sonic-cfggen<br/>(config CLI のみ)"]')
        lines.append("  CLI --> SC")
        for i, (tbl, dm) in enumerate(tables_daemons):
            cn = f"CDB{i}"
            lines.append(f'  {cn}[("CONFIG_DB<br/>{tbl}")]')
            lines.append(f"  SC --> {cn}")
            if dm:
                dn = f"DM{i}"
                lines.append(f'  {dn}["{dm}"]')
                lines.append(f"  {cn} --> {dn}")
    lines.append("```")
    return "\n".join(lines)


def render_block(command: str, tables_daemons: list[tuple[str, Optional[str]]], show_dir: bool) -> str:
    mermaid = build_mermaid(command, tables_daemons, show_dir)
    direction = "show 系 (CONFIG_DB → CLI)" if show_dir else "config 系 (CLI → CONFIG_DB → daemon)"
    return (
        f"{BEGIN_TAG}\n"
        f"### データフロー (自動生成)\n\n"
        f"{mermaid}\n\n"
        f"!!! note \"凡例\"\n"
        f"    {direction} のミニ図。テーブル → daemon 対応は "
        f"`docs/reference/config-db-orch-map.md` から機械生成。\n"
        f"{END_TAG}"
    )


BLOCK_RE = re.compile(
    re.escape(BEGIN_TAG) + r".*?" + re.escape(END_TAG) + r"\n?",
    re.DOTALL,
)


def insert_block(text: str, block: str) -> str:
    if BEGIN_TAG in text:
        return BLOCK_RE.sub(block + "\n", text, count=1)

    # Preferred: just before `<!-- topics-back-ref -->`
    idx = text.find("<!-- topics-back-ref -->")
    if idx >= 0:
        return text[:idx] + block + "\n\n" + text[idx:]

    # Fallback: just before `<!-- ref-triangle:start -->`
    idx = text.find("<!-- ref-triangle:start -->")
    if idx >= 0:
        return text[:idx] + block + "\n\n" + text[idx:]

    # Fallback: before `## 引用元`
    m = re.search(r"\n## 引用元\n", text)
    if m:
        return text[: m.start() + 1] + block + "\n" + text[m.start() + 1:]

    # Last resort: append
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="Fail if any file would change")
    args = ap.parse_args()

    mapping = parse_map()
    print(f"[gen_cli_mermaid] parsed {len(mapping)} table→daemon entries from orch-map", file=sys.stderr)

    changed = 0
    inserted = 0
    skipped_no_cdb = 0
    skipped_no_map = 0
    drift: list[str] = []

    for page in sorted(PAGES_DIR.glob("*.md")):
        slug = page.stem
        if slug == "index":
            continue
        text = page.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        cdb_tables = fm["config_db"]
        if not cdb_tables:
            skipped_no_cdb += 1
            continue

        # resolve daemons (only keep tables with a known daemon for config pages;
        # for show pages, we keep them regardless since direction is CDB->CLI)
        show_dir = is_show_page(slug)
        td: list[tuple[str, Optional[str]]] = []
        for tbl in cdb_tables:
            dm = mapping.get(tbl)
            if not show_dir and not dm:
                continue
            td.append((tbl, dm))
        if not td:
            skipped_no_map += 1
            continue

        # cap at 4 tables to keep diagrams readable
        td = td[:4]

        # Derive command label: prefer first related.cli entry, else slug-based
        if fm["cli"]:
            command = fm["cli"][0]
        else:
            command = slug_to_command(slug)

        block = render_block(command, td, show_dir)
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
        f"[gen_cli_mermaid] inserted/updated: {changed} | total with block: {inserted} | "
        f"skipped (no config_db): {skipped_no_cdb} | skipped (no daemon match): {skipped_no_map}",
        file=sys.stderr,
    )
    if args.check and drift:
        print("[gen_cli_mermaid] drift detected in:", file=sys.stderr)
        for p in drift:
            print(f"  - {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
