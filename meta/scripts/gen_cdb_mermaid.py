#!/usr/bin/env python3
"""Generate mini data-flow mermaid blocks for CONFIG_DB reference pages.

Sources mapping from `docs/reference/config-db-orch-map.md` and injects a
`<!-- cdb-mermaid -->` block right after the `## 概要` section body in each
`docs/reference/config-db/<slug>.md` page whose first `related.config_db`
table (or slug-derived guess) is present in the mapping.

Usage:
    python3 meta/scripts/gen_cdb_mermaid.py        # write
    python3 meta/scripts/gen_cdb_mermaid.py --check  # diff only

The block is idempotent — re-running with no source changes yields no diff.

Non-CONFIG_DB pages (APPL_DB, STATE_DB, COUNTERS_DB, etc.) are detected by
title keywords and are skipped.  Any previously mis-inserted block is removed.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / "docs" / "reference" / "config-db-orch-map.md"
PAGES_DIR = ROOT / "docs" / "reference" / "config-db"

BEGIN_TAG = "<!-- cdb-mermaid -->"
END_TAG = "<!-- /cdb-mermaid -->"

ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")


def parse_map() -> dict[str, dict[str, Optional[str]]]:
    """Parse the markdown table rows.

    Returns: dict from TABLE_NAME -> {daemon, app_db_table, sai}.
    """
    result: dict[str, dict[str, Optional[str]]] = {}
    text = MAP_FILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        table, subscriber, appl, sai = m.group(1), m.group(2), m.group(3), m.group(4)
        if table in ("CONFIG_DB", "CONFIG_DB テーブル"):
            continue
        # extract daemon (first identifier-ish token in subscriber)
        daemon = extract_daemon(subscriber)
        app_db_table = extract_app_db(subscriber, appl)
        sai_attrs = extract_sai(sai)
        # don't overwrite if already present (first wins → port primary entry)
        if table in result:
            continue
        result[table] = {
            "daemon": daemon,
            "app_db_table": app_db_table,
            "sai": sai_attrs,
            "raw_subscriber": subscriber,
        }
    return result


def extract_daemon(subscriber: str) -> Optional[str]:
    """Pick the first daemon/orch identifier from subscriber cell."""
    # patterns: `portmgrd` → `PortsOrch`, `AclOrch` (直接 CFG)
    m = re.search(r"`([A-Za-z][A-Za-z0-9_-]*)`", subscriber)
    if m:
        return m.group(1)
    m = re.search(r"([A-Z][A-Za-z0-9]*Orch)", subscriber)
    if m:
        return m.group(1)
    return None


def extract_app_db(subscriber: str, appl: str) -> Optional[str]:
    """Find APP_DB table name. Prefer explicit APP_* mention."""
    for cell in (subscriber, appl):
        m = re.search(r"`(APP_[A-Z0-9_]+)`", cell)
        if m:
            return m.group(1)
    if "✓" in appl:
        return "APP_DB"
    return None


def extract_sai(sai: str) -> Optional[str]:
    """Find the SAI api/object mentioned in the SAI column."""
    m = re.search(r"`(sai_[a-z0-9_]+)`", sai)
    if m:
        return m.group(1)
    # bare token sai_xxx
    m = re.search(r"(sai_[a-z0-9_]+)", sai)
    if m:
        return m.group(1)
    return None


# Fallback dictionary for tables not parseable from orch-map (or whose
# orch-map row lacks a daemon/app/sai token). Manually curated from the
# corresponding CONFIG_DB ref pages. daemon は CONFIG_DB の直接 subscriber、
# app_db_table と sai は経路がある場合のみ指定（None → 図には出ない）。
FALLBACK_MAP: dict[str, dict[str, Optional[str]]] = {
    "AS_PATH_SET": {"daemon": "bgpcfgd", "app_db_table": None, "sai": None},
    "AUTO_TECHSUPPORT": {"daemon": "coredump_gen_handler", "app_db_table": None, "sai": None},
    "AUTO_TECHSUPPORT_FEATURE": {"daemon": "coredump_gen_handler", "app_db_table": None, "sai": None},
    "BGP_ALLOWED_PREFIXES": {"daemon": "bgpcfgd", "app_db_table": None, "sai": None},
    "BGP_GLOBALS_AF_AGGREGATE_ADDR": {"daemon": "frrcfgd", "app_db_table": None, "sai": None},
    "BGP_GLOBALS_AF_NETWORK": {"daemon": "frrcfgd", "app_db_table": None, "sai": None},
    "BGP_NEIGHBOR_AF": {"daemon": "frrcfgd", "app_db_table": None, "sai": None},
    "BGP_PEER_GROUP_AF": {"daemon": "frrcfgd", "app_db_table": None, "sai": None},
    "COMMUNITY_SET": {"daemon": "bgpcfgd", "app_db_table": None, "sai": None},
    "CONSOLE_PORT": {"daemon": "consutil", "app_db_table": None, "sai": None},
    "DEVICE_NEIGHBOR": {"daemon": "lldpmgrd", "app_db_table": None, "sai": None},
    "DEVICE_NEIGHBOR_METADATA": {"daemon": "lldpmgrd", "app_db_table": None, "sai": None},
    "DEVICE_RUNTIME_METADATA": {"daemon": "sonic-cfggen", "app_db_table": None, "sai": None},
    "DHCPV4_RELAY": {"daemon": "sonic-dhcpv4-relay", "app_db_table": None, "sai": None},
    "FLEX_COUNTER_TABLE": {"daemon": "syncd", "app_db_table": None, "sai": "sai_*_stats"},
    "HEARTBEAT": {"daemon": "process-monitor", "app_db_table": None, "sai": None},
    "KUBERNETES_MASTER": {"daemon": "ctrmgrd", "app_db_table": None, "sai": None},
    "LOSSLESS_TRAFFIC_PATTERN": {"daemon": "buffermgrd", "app_db_table": "APP_BUFFER_PROFILE_TABLE", "sai": "sai_buffer_api"},
    "MUX_LINKMGR": {"daemon": "linkmgrd", "app_db_table": None, "sai": None},
    "PREFIX_LIST": {"daemon": "bgpcfgd", "app_db_table": None, "sai": None},
    "PREFIX_SET": {"daemon": "frrcfgd", "app_db_table": None, "sai": None},
    "STATIC_ROUTE": {"daemon": "bgpcfgd", "app_db_table": "APP_ROUTE_TABLE", "sai": "sai_route_api"},
    "SUBNET_DECAP": {"daemon": "tunnelmgrd", "app_db_table": "APP_TUNNEL_DECAP_TABLE", "sai": "sai_tunnel_api"},
    "SYSLOG_CONFIG_FEATURE": {"daemon": "containercfgd", "app_db_table": None, "sai": None},
    "TELEMETRY": {"daemon": "telemetry", "app_db_table": None, "sai": None},
    "TELEMETRY_CLIENT": {"daemon": "telemetry", "app_db_table": None, "sai": None},
    "TUNNEL_DECAP_TABLE": {"daemon": "tunneldecaporch", "app_db_table": "APP_TUNNEL_DECAP_TABLE", "sai": "sai_tunnel_api"},
    "WARM_RESTART": {"daemon": "warmboot-finalizer", "app_db_table": None, "sai": None},
}


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

# Keywords in the page title that indicate the page is NOT a CONFIG_DB page.
# These pages must never receive (or retain) the auto-generated cdb-mermaid block.
NON_CONFIG_DB_TITLE_MARKERS = (
    "APPL_DB",
    "(APPL_DB)",
    "STATE_DB",
    "COUNTERS_DB",
    "EVENT_DB",
    "ERROR_DB",
    "CHASSIS_APP_DB",
    "CHASSIS_STATE_DB",
    "FLEX_COUNTER_DB",
    "APPL_STATE_DB",
)

# Phrases in the description that indicate the page primarily documents a non-CONFIG_DB table.
NON_CONFIG_DB_DESC_MARKERS = (
    "APP_DB に保持",
    "APPL_DB に保持",
    "APP_DB 上の",
    "APPL_DB 上の",
    "APP_DB のテーブル",
    "APPL_DB のテーブル",
)


def get_title(text: str) -> Optional[str]:
    """Extract title value from frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    title_m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', m.group(1), re.MULTILINE)
    if title_m:
        return title_m.group(1).strip()
    return None


def get_description(text: str) -> Optional[str]:
    """Extract description value from frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    desc_m = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', m.group(1), re.MULTILINE)
    if desc_m:
        return desc_m.group(1).strip()
    return None


def is_non_config_db_page(page: pathlib.Path, text: str) -> bool:
    """Return True if this page documents a non-CONFIG_DB table (APPL_DB, STATE_DB, etc.).

    Such pages must never receive the auto-generated cdb-mermaid block.  Any
    existing block that was incorrectly inserted will be removed.
    """
    title = get_title(text) or ""
    for marker in NON_CONFIG_DB_TITLE_MARKERS:
        if marker in title:
            return True
    # Slug-based fallback: slugs starting with "appl-" are APPL_DB pages
    # even if the title does not explicitly say so.
    if page.stem.startswith("appl-"):
        return True
    # Description-based fallback: page describes a table that lives in APP_DB/APPL_DB
    desc = get_description(text) or ""
    for marker in NON_CONFIG_DB_DESC_MARKERS:
        if marker in desc:
            return True
    return False


def get_first_config_db_table(text: str) -> Optional[str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm = m.group(1)
    # find `config_db:` block under `related:`
    cdb_match = re.search(r"\n  config_db:\s*\n((?:    - .+\n)+)", fm)
    if not cdb_match:
        # try inline empty
        return None
    first = cdb_match.group(1).splitlines()[0].strip()
    # `- TABLE_NAME`
    m2 = re.match(r"-\s+(.+)$", first)
    if not m2:
        return None
    return m2.group(1).strip()


def slug_to_table(slug: str) -> str:
    return slug.upper().replace("-", "_")


def build_mermaid(table: str, info: dict[str, Optional[str]]) -> str:
    daemon = info["daemon"]
    app = info["app_db_table"]
    sai = info["sai"]

    lines = ["```mermaid", "flowchart LR"]
    lines.append(f'  CDB[("CONFIG_DB<br/>{table}")]')
    prev = "CDB"
    if daemon:
        node = "DM"
        lines.append(f'  {node}["{daemon}"]')
        lines.append(f"  {prev} --> {node}")
        prev = node
    if app:
        node = "APPDB"
        lines.append(f'  {node}[("APP_DB<br/>{app}")]')
        lines.append(f"  {prev} --> {node}")
        prev = node
        lines.append('  SYNCD["syncd"]')
        lines.append(f"  {prev} --> SYNCD")
        prev = "SYNCD"
    if sai:
        node = "SAI"
        lines.append(f'  {node}["SAI<br/>{sai}"]')
        lines.append(f"  {prev} --> {node}")
    lines.append("```")
    return "\n".join(lines)


def render_block(table: str, info: dict) -> str:
    mermaid = build_mermaid(table, info)
    return (
        f"{BEGIN_TAG}\n"
        f"### データフロー (自動生成)\n\n"
        f"{mermaid}\n\n"
        f"!!! note \"凡例\"\n"
        f"    CONFIG_DB から SAI までの典型経路を `docs/reference/config-db-orch-map.md` "
        f"から機械生成したミニ図。詳細・例外は本ページ本文と対応表を参照。\n"
        f"{END_TAG}"
    )


BLOCK_RE = re.compile(
    re.escape(BEGIN_TAG) + r".*?" + re.escape(END_TAG) + r"\n?",
    re.DOTALL,
)


def insert_block(text: str, block: str) -> str:
    """Insert/replace the cdb-mermaid block.

    If an existing block is present, replace it. Otherwise insert it after
    the `## 概要` section body (i.e., before the next `## ` header) or, if
    that section is missing, right after the frontmatter.
    """
    if BEGIN_TAG in text:
        return BLOCK_RE.sub(block + "\n", text, count=1)

    # find end of frontmatter
    m = FRONTMATTER_RE.match(text)
    insert_at = m.end() if m else 0

    # search for `## 概要` after frontmatter
    gaiyou = re.search(r"\n## 概要\n", text[insert_at:])
    if gaiyou:
        start = insert_at + gaiyou.end()
        next_h2 = re.search(r"\n## ", text[start:])
        if next_h2:
            pos = start + next_h2.start()
            return text[:pos] + "\n" + block + "\n" + text[pos:]
        return text + "\n" + block + "\n"
    # fallback: after frontmatter
    return text[:insert_at] + "\n" + block + "\n" + text[insert_at:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="Fail if any file would change")
    args = ap.parse_args()

    mapping = parse_map()
    print(f"[gen_cdb_mermaid] parsed {len(mapping)} CONFIG_DB tables from orch-map", file=sys.stderr)

    changed = 0
    inserted = 0
    skipped_no_map = 0
    removed_non_cdb = 0
    drift: list[str] = []

    for page in sorted(PAGES_DIR.glob("*.md")):
        if page.name == "index.md":
            continue
        text = page.read_text(encoding="utf-8")

        # --- Non-CONFIG_DB pages: remove any wrongly-inserted block and skip ---
        if is_non_config_db_page(page, text):
            if BEGIN_TAG in text:
                if END_TAG in text:
                    # Complete block: remove begin...end tags plus content
                    new_text = BLOCK_RE.sub("", text)
                else:
                    # Orphaned open tag only: remove the lone BEGIN_TAG line
                    new_text = re.sub(
                        r"[ \t]*" + re.escape(BEGIN_TAG) + r"[ \t]*\n?",
                        "",
                        text,
                    )
                if new_text != text:
                    if args.check:
                        drift.append(str(page.relative_to(ROOT)))
                    else:
                        page.write_text(new_text, encoding="utf-8")
                    changed += 1
                    removed_non_cdb += 1
            continue

        table = get_first_config_db_table(text)
        if not table:
            table = slug_to_table(page.stem)
        info = mapping.get(table)
        if not info:
            # also try uppercased slug
            alt = slug_to_table(page.stem)
            info = mapping.get(alt)
            if info:
                table = alt
        # fallback dictionary if mapping missing or empty
        if (info is None) or not (info["daemon"] or info["app_db_table"] or info["sai"]):
            fb = FALLBACK_MAP.get(table) or FALLBACK_MAP.get(slug_to_table(page.stem))
            if fb:
                info = fb
        if info is None:
            skipped_no_map += 1
            continue
        # need at least daemon or app or sai
        if not (info["daemon"] or info["app_db_table"] or info["sai"]):
            skipped_no_map += 1
            continue
        block = render_block(table, info)
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
        f"[gen_cdb_mermaid] inserted/updated: {changed} | total with block: {inserted} | "
        f"skipped (no mapping): {skipped_no_map} | removed (non-CONFIG_DB): {removed_non_cdb}",
        file=sys.stderr,
    )
    if args.check and drift:
        print("[gen_cdb_mermaid] drift detected in:", file=sys.stderr)
        for p in drift:
            print(f"  - {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
