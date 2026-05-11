#!/usr/bin/env python3
"""Back-fill frontmatter `related.{cli,config_db,yang}` for pages where all
three lists are empty (or absent).

Two modes:

* **default** (legacy): only the original heuristics
  - `config X` / `show X` / `clear X` patterns -> related.cli
  - Uppercase-snake `[TABLE]` / `` `TABLE` `` tokens -> related.config_db
  - `sonic-<name>` tokens -> related.yang

* **aggressive**: enables additional heuristics on top of the above
  - **glossary term match**: scans body for `#term-<slug>` glossary anchor
    references; the term slug is then expanded into candidate CDB/CLI/YANG
    references by prefix matching (e.g. `#term-bgp` -> any `bgp-*` CDB and
    any `sonic-bgp-*` YANG file).
  - **title / slug token match**: tokenizes the page title and filename slug
    into keywords (length >= 3, alphanum), then for each keyword finds CDB /
    CLI / YANG ref pages whose slug *starts with* that keyword. This catches
    e.g. `bgp-multicast-source-discovery-protocol.md` -> `BGP_*` CDB.
  - **via-CLI CDB inference**: for each `related.cli` we end up suggesting,
    open the corresponding `docs/reference/cli/<slug>.md` and harvest its
    own `related.config_db` to add to the page.

Each list is capped at 7 entries (5 in default mode), ranked by occurrence
frequency.

Only pages whose `related` is fully empty are touched. Existing non-empty
fields are never overwritten.

This script is not part of CI (non-deterministic vs. evolving content).

Usage:
    meta/scripts/backfill_related.py [--dry-run] [--mode default|aggressive]
                                    [--root docs] [--limit N]
                                    [--targets DIR[,DIR...]]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml


# Wider scan list — aggressive mode benefits from these.
DEFAULT_TARGET_DIRS = [
    "docs/reference/runbooks",
    "docs/management",
    "docs/architecture",
    "docs/overlay",
    "docs/routing",
    "docs/switching",
    "docs/internals",
    "docs/topics",
    "docs/system",
    "docs/platform",
    "docs/acl-qos",
    "docs/guides",
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
    """Map normalized command form -> command form for known refs."""
    out: dict[str, str] = {}
    d = root / CLI_REF_DIR
    if not d.is_dir():
        return out
    for f in d.iterdir():
        if f.suffix != ".md" or f.name == "index.md":
            continue
        slug = f.stem
        cmd = slug.replace("-", " ")
        out[cmd] = cmd
    return out


def load_cli_slugs(root: Path) -> dict[str, str]:
    """Map filename slug (`config-aaa`) -> command form (`config aaa`)."""
    out: dict[str, str] = {}
    d = root / CLI_REF_DIR
    if not d.is_dir():
        return out
    for f in d.iterdir():
        if f.suffix != ".md" or f.name == "index.md":
            continue
        out[f.stem] = f.stem.replace("-", " ")
    return out


def load_cdb_index(root: Path) -> set[str]:
    out: set[str] = set()
    d = root / CDB_REF_DIR
    if not d.is_dir():
        return out
    for f in d.iterdir():
        if f.suffix != ".md" or f.name == "index.md":
            continue
        upper = f.stem.upper().replace("-", "_")
        out.add(upper)
    return out


def load_cdb_slugs(root: Path) -> dict[str, str]:
    """Map filename slug -> UPPER_SNAKE table name."""
    out: dict[str, str] = {}
    d = root / CDB_REF_DIR
    if not d.is_dir():
        return out
    for f in d.iterdir():
        if f.suffix != ".md" or f.name == "index.md":
            continue
        out[f.stem] = f.stem.upper().replace("-", "_")
    return out


def load_yang_index(root: Path) -> set[str]:
    out: set[str] = set()
    d = root / YANG_REF_DIR
    if not d.is_dir():
        return out
    for f in d.iterdir():
        if f.suffix != ".md" or f.name == "index.md":
            continue
        out.add(f.stem)
    return out


def load_cli_to_cdb(root: Path) -> dict[str, list[str]]:
    """For each CLI ref page, harvest its frontmatter `related.config_db`."""
    out: dict[str, list[str]] = {}
    d = root / CLI_REF_DIR
    if not d.is_dir():
        return out
    for f in d.iterdir():
        if f.suffix != ".md" or f.name == "index.md":
            continue
        try:
            t = f.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, _ = split_frontmatter(t)
        if not fm:
            continue
        rel = fm.get("related") or {}
        cdb = rel.get("config_db") if isinstance(rel, dict) else None
        if isinstance(cdb, list) and cdb:
            out[f.stem.replace("-", " ")] = [str(x) for x in cdb if x]
    return out


# ---------- extraction (legacy) ----------

CLI_PAT = re.compile(
    r"\b(config|show|clear)\b((?:[ \t]+[a-z][a-z0-9\-]*){1,3})",
    re.IGNORECASE,
)

CDB_PAT_BRACKET = re.compile(r"\[([A-Z][A-Z0-9_]{2,})\]")
CDB_PAT_BACKTICK = re.compile(r"`([A-Z][A-Z0-9_]{2,})`")

YANG_PAT = re.compile(r"\b(sonic-[a-z0-9\-]+)\b")

# ---------- extraction (aggressive) ----------

# `#term-foo` anchors in body (markdown link target into glossary).
GLOSSARY_ANCHOR_PAT = re.compile(r"#term-([a-z0-9][a-z0-9_\-]*)")

# Slug / title tokens: alphanumeric runs >=3 chars.
TOKEN_PAT = re.compile(r"[a-z0-9]{3,}")

# Stop tokens that are too generic to match (would explode the result set).
STOP_TOKENS = {
    "the", "and", "for", "with", "from", "into", "over", "ref", "doc",
    "docs", "page", "design", "internals", "concept", "concepts",
    "operations", "overview", "limitations", "architecture", "intro",
    "introduction", "topic", "topics", "guide", "guides", "feature",
    "high", "level", "hld", "hlds", "sonic", "based", "support", "supports",
    "supporting", "manager", "daemon", "module", "modules", "table", "tables",
    "config", "show", "clear", "yang", "cli", "ref", "reference", "system",
    "platform", "common", "general", "control", "data", "plane", "planes",
    "main", "list", "type", "types", "set", "get", "use", "uses", "used",
    "user", "users", "case", "cases", "summary", "section",
}


def extract_cli(body: str, cli_idx: dict[str, str], cap: int) -> list[str]:
    counter: Counter = Counter()
    for m in CLI_PAT.finditer(body):
        verb = m.group(1).lower()
        tail = m.group(2).strip().lower()
        tokens = tail.split()
        for n in range(len(tokens), 0, -1):
            cand = (verb + " " + " ".join(tokens[:n])).strip()
            if cand in cli_idx:
                counter[cand] += 1
                break
        else:
            if verb in cli_idx:
                counter[verb] += 1
    return [k for k, _ in counter.most_common(cap)]


def extract_cdb(body: str, cdb_idx: set[str], cap: int) -> list[str]:
    counter: Counter = Counter()
    for pat in (CDB_PAT_BRACKET, CDB_PAT_BACKTICK):
        for m in pat.finditer(body):
            tok = m.group(1)
            if tok in cdb_idx:
                counter[tok] += 1
    return [k for k, _ in counter.most_common(cap)]


def extract_yang(body: str, yang_idx: set[str], cap: int) -> list[str]:
    counter: Counter = Counter()
    for m in YANG_PAT.finditer(body):
        tok = m.group(1).lower()
        if tok in yang_idx:
            counter[tok] += 1
    return [k for k, _ in counter.most_common(cap)]


def _slug_tokens(*texts: str) -> list[str]:
    """Tokenize the given strings into useful lowercased keywords."""
    out: list[str] = []
    for t in texts:
        if not t:
            continue
        for m in TOKEN_PAT.finditer(t.lower()):
            tok = m.group(0)
            if tok in STOP_TOKENS:
                continue
            if tok.isdigit():
                continue
            out.append(tok)
    return out


def _prefix_match_cdb(tokens: list[str], cdb_slugs: dict[str, str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        for slug, table in cdb_slugs.items():
            if slug == tok or slug.startswith(tok + "-") or slug.startswith(tok + "_"):
                if table not in seen:
                    seen.add(table)
                    out.append(table)
    return out


def _prefix_match_yang(tokens: list[str], yang_idx: set[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for tok in tokens:
        target = f"sonic-{tok}"
        for slug in yang_idx:
            if slug == target or slug.startswith(target + "-"):
                if slug not in seen:
                    seen.add(slug)
                    out.append(slug)
    return out


def _prefix_match_cli(tokens: list[str], cli_slugs: dict[str, str]) -> list[str]:
    """Find CLI ref pages whose slug starts with `<verb>-<token>`."""
    out: list[str] = []
    seen: set[str] = set()
    verbs = ("config", "show", "clear")
    for tok in tokens:
        for slug, cmd in cli_slugs.items():
            for v in verbs:
                if slug == f"{v}-{tok}" or slug.startswith(f"{v}-{tok}-"):
                    if cmd not in seen:
                        seen.add(cmd)
                        out.append(cmd)
                    break
    return out


def extract_aggressive(
    body: str,
    fm: dict,
    path: Path,
    cli_slugs: dict[str, str],
    cdb_slugs: dict[str, str],
    yang_idx: set[str],
    cli_to_cdb: dict[str, list[str]],
) -> tuple[list[str], list[str], list[str]]:
    """Return additional (cli, cdb, yang) candidates from aggressive heuristics.

    These are appended to the legacy results, deduped & ranked by frequency.
    """
    extra_cli: Counter = Counter()
    extra_cdb: Counter = Counter()
    extra_yang: Counter = Counter()

    # 1. glossary anchor matches in body
    glossary_terms = set()
    for m in GLOSSARY_ANCHOR_PAT.finditer(body):
        term = m.group(1).replace("_", "-")
        glossary_terms.add(term)

    # 2. title / slug tokens
    title = str(fm.get("title") or "")
    slug = path.stem
    tokens = _slug_tokens(title, slug)
    # also include glossary terms as tokens
    for term in glossary_terms:
        tokens.append(term)
    # dedupe but keep order
    seen_t: set[str] = set()
    uniq_tokens = []
    for t in tokens:
        if t not in seen_t:
            seen_t.add(t)
            uniq_tokens.append(t)

    for tbl in _prefix_match_cdb(uniq_tokens, cdb_slugs):
        extra_cdb[tbl] += 1
    for yslug in _prefix_match_yang(uniq_tokens, yang_idx):
        extra_yang[yslug] += 1
    for cmd in _prefix_match_cli(uniq_tokens, cli_slugs):
        extra_cli[cmd] += 1

    return (
        [k for k, _ in extra_cli.most_common()],
        [k for k, _ in extra_cdb.most_common()],
        [k for k, _ in extra_yang.most_common()],
    )


def _merge_capped(*lists: list[str], cap: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for lst in lists:
        for item in lst:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
            if len(out) >= cap:
                return out
    return out


# ---------- main ----------

def process_file(
    path: Path,
    cli_idx,
    cli_slugs,
    cdb_idx,
    cdb_slugs,
    yang_idx,
    cli_to_cdb,
    mode: str,
    dry_run: bool,
):
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        return None
    if not related_is_empty(fm):
        return None

    aggressive = mode == "aggressive"
    cap = 7 if aggressive else 5

    cli = extract_cli(body, cli_idx, cap)
    cdb = extract_cdb(body, cdb_idx, cap)
    yng = extract_yang(body, yang_idx, cap)

    if aggressive:
        ex_cli, ex_cdb, ex_yang = extract_aggressive(
            body, fm, path, cli_slugs, cdb_slugs, yang_idx, cli_to_cdb
        )
        # via-CLI CDB: for each CLI candidate, pick up its related.config_db
        via_cli_cdb: list[str] = []
        for cmd in list(cli) + ex_cli:
            for tbl in cli_to_cdb.get(cmd, []):
                via_cli_cdb.append(tbl)

        cli = _merge_capped(cli, ex_cli, cap=cap)
        cdb = _merge_capped(cdb, ex_cdb, via_cli_cdb, cap=cap)
        yng = _merge_capped(yng, ex_yang, cap=cap)

    if not cli and not cdb and not yng:
        return ("noop", path, [], [], [])

    rel = fm.get("related") or {}
    if not isinstance(rel, dict):
        rel = {}
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
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return ("update", path, cli, cdb, yng)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=".", help="repo root")
    ap.add_argument(
        "--mode",
        choices=("default", "aggressive"),
        default="default",
        help="default = legacy heuristics; aggressive = glossary + slug-token + via-CLI heuristics",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="maximum number of pages to UPDATE (0 = no limit)",
    )
    ap.add_argument(
        "--targets",
        default=",".join(DEFAULT_TARGET_DIRS),
        help="comma-separated directories to scan",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    cli_idx = load_cli_index(root)
    cli_slugs = load_cli_slugs(root)
    cdb_idx = load_cdb_index(root)
    cdb_slugs = load_cdb_slugs(root)
    yang_idx = load_yang_index(root)
    cli_to_cdb = load_cli_to_cdb(root) if args.mode == "aggressive" else {}

    target_dirs = [d.strip() for d in args.targets.split(",") if d.strip()]

    targets: list[Path] = []
    for d in target_dirs:
        full = root / d
        if not full.is_dir():
            continue
        for p in sorted(full.rglob("*.md")):
            if p.name == "index.md":
                continue
            targets.append(p)

    updated = 0
    skipped_noop = 0
    for path in targets:
        if args.limit and updated >= args.limit:
            break
        res = process_file(
            path,
            cli_idx,
            cli_slugs,
            cdb_idx,
            cdb_slugs,
            yang_idx,
            cli_to_cdb,
            args.mode,
            args.dry_run,
        )
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
        f"(mode={args.mode}, dry_run={args.dry_run})",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
