#!/usr/bin/env python3
"""Back-fill frontmatter `related.{cli,config_db,yang}` for pages where all
three lists are empty (or absent).

Heuristics (intentionally coarse):
  * `config X` / `show X` / `clear X` patterns -> related.cli, matched against
    existing `docs/reference/cli/*.md` filenames (slugified).
  * Uppercase-snake tokens (TABLE_NAME) appearing in [TABLE_NAME] or backticks
    -> related.config_db, matched against existing `docs/reference/config-db/*.md`.
  * `sonic-<name>` tokens -> related.yang, matched against existing
    `docs/reference/yang/*.md`.

Each list is capped at 5 entries, ranked by occurrence frequency.

Only pages whose `related` is fully empty are touched. Existing non-empty
fields are never overwritten.

This script is not part of CI (non-deterministic vs. evolving content).

Usage:
    meta/scripts/backfill_related.py [--dry-run] [--root docs]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

import yaml


TARGET_DIRS = [
    "docs/reference/runbooks",
    "docs/management",
    "docs/architecture",
]

CLI_REF_DIR = "docs/reference/cli"
CDB_REF_DIR = "docs/reference/config-db"
YANG_REF_DIR = "docs/reference/yang"

# ---------- frontmatter helpers ----------

FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def split_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return None, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, text
    body = text[m.end():]
    return data, body


def dump_frontmatter(data: dict) -> str:
    return yaml.safe_dump(
        data, allow_unicode=True, sort_keys=False, default_flow_style=False
    )


def related_is_empty(fm: dict) -> bool:
    rel = fm.get("related") or {}
    if not isinstance(rel, dict):
        return False
    for key in ("cli", "config_db", "yang"):
        v = rel.get(key) or []
        if v:
            return False
    return True


# ---------- reference indices ----------

def load_cli_index(root: Path) -> dict[str, str]:
    """Map normalized slug (with spaces) -> CLI command form for known refs.

    e.g. file `config-aaa.md` -> {"config aaa": "config aaa"}.
    Also handle 2-word and 3-word commands by their filename slug.
    """
    out = {}
    d = root / CLI_REF_DIR
    if not d.is_dir():
        return out
    for f in d.iterdir():
        if f.suffix != ".md" or f.name == "index.md":
            continue
        slug = f.stem  # e.g. "config-aaa"
        cmd = slug.replace("-", " ")
        out[cmd] = cmd
    return out


def load_cdb_index(root: Path) -> set[str]:
    out = set()
    d = root / CDB_REF_DIR
    if not d.is_dir():
        return out
    for f in d.iterdir():
        if f.suffix != ".md" or f.name == "index.md":
            continue
        # filenames are kebab-case lower; CONFIG_DB tables are UPPER_SNAKE.
        # convert: "acl-rule" -> "ACL_RULE"
        upper = f.stem.upper().replace("-", "_")
        out.add(upper)
    return out


def load_yang_index(root: Path) -> set[str]:
    out = set()
    d = root / YANG_REF_DIR
    if not d.is_dir():
        return out
    for f in d.iterdir():
        if f.suffix != ".md" or f.name == "index.md":
            continue
        # e.g. "sonic-bgp-global.md" -> "sonic-bgp-global"
        out.add(f.stem)
    return out


# ---------- extraction ----------

CLI_VERBS = ("config", "show", "clear")
CLI_PAT = re.compile(
    r"\b(config|show|clear)\b((?:[ \t]+[a-z][a-z0-9\-]*){1,3})",
    re.IGNORECASE,
)

CDB_PAT_BRACKET = re.compile(r"\[([A-Z][A-Z0-9_]{2,})\]")
CDB_PAT_BACKTICK = re.compile(r"`([A-Z][A-Z0-9_]{2,})`")

YANG_PAT = re.compile(r"\b(sonic-[a-z0-9\-]+)\b")


def extract_cli(body: str, cli_idx: dict[str, str]) -> list[str]:
    counter: Counter = Counter()
    # strip code fences first to reduce noise? we keep them; CLI is often in them.
    for m in CLI_PAT.finditer(body):
        verb = m.group(1).lower()
        tail = m.group(2).strip().lower()
        tokens = tail.split()
        # try longest to shortest match
        for n in range(len(tokens), 0, -1):
            cand = (verb + " " + " ".join(tokens[:n])).strip()
            if cand in cli_idx:
                counter[cand] += 1
                break
        else:
            cand = verb
            if cand in cli_idx:
                counter[cand] += 1
    return [k for k, _ in counter.most_common(5)]


def extract_cdb(body: str, cdb_idx: set[str]) -> list[str]:
    counter: Counter = Counter()
    for pat in (CDB_PAT_BRACKET, CDB_PAT_BACKTICK):
        for m in pat.finditer(body):
            tok = m.group(1)
            if tok in cdb_idx:
                counter[tok] += 1
    return [k for k, _ in counter.most_common(5)]


def extract_yang(body: str, yang_idx: set[str]) -> list[str]:
    counter: Counter = Counter()
    for m in YANG_PAT.finditer(body):
        tok = m.group(1).lower()
        if tok in yang_idx:
            counter[tok] += 1
    return [k for k, _ in counter.most_common(5)]


# ---------- main ----------

def process_file(path: Path, cli_idx, cdb_idx, yang_idx, dry_run: bool):
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        return None
    if not related_is_empty(fm):
        return None

    cli = extract_cli(body, cli_idx)
    cdb = extract_cdb(body, cdb_idx)
    yng = extract_yang(body, yang_idx)
    if not cli and not cdb and not yng:
        return ("noop", path, [], [], [])

    rel = fm.get("related") or {}
    if not isinstance(rel, dict):
        rel = {}
    # only fill empties
    if cli and not (rel.get("cli") or []):
        rel["cli"] = cli
    else:
        rel.setdefault("cli", rel.get("cli") or [])
    if cdb and not (rel.get("config_db") or []):
        rel["config_db"] = cdb
    else:
        rel.setdefault("config_db", rel.get("config_db") or [])
    if yng and not (rel.get("yang") or []):
        rel["yang"] = yng
    else:
        rel.setdefault("yang", rel.get("yang") or [])
    fm["related"] = rel

    new_text = "---\n" + dump_frontmatter(fm) + "---\n" + body
    if dry_run:
        return ("update", path, cli, cdb, yng)
    path.write_text(new_text, encoding="utf-8")
    return ("update", path, cli, cdb, yng)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=".", help="repo root")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    cli_idx = load_cli_index(root)
    cdb_idx = load_cdb_index(root)
    yang_idx = load_yang_index(root)

    targets: list[Path] = []
    for d in TARGET_DIRS:
        full = root / d
        if not full.is_dir():
            continue
        for p in sorted(full.iterdir()):
            if p.suffix == ".md" and p.name != "index.md":
                targets.append(p)

    updated = 0
    skipped_noop = 0
    for path in targets:
        res = process_file(path, cli_idx, cdb_idx, yang_idx, args.dry_run)
        if res is None:
            continue
        kind, p, cli, cdb, yng = res
        rel_path = p.relative_to(root)
        if kind == "update":
            updated += 1
            print(
                f"[{'DRY' if args.dry_run else 'UPDATE'}] {rel_path} "
                f"cli={cli} config_db={cdb} yang={yng}",
                file=sys.stderr,
            )
        elif kind == "noop":
            skipped_noop += 1
            print(f"[NOOP] {rel_path} (no matches found)", file=sys.stderr)

    print(
        f"\nSummary: {updated} updated, {skipped_noop} noop "
        f"(dry_run={args.dry_run})",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
