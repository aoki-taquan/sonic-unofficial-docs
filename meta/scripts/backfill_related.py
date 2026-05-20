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
  - **STATE_DB / COUNTERS_DB / ASIC_DB inference**: tokens of the form
    `STATE_DB:FOO_TABLE`, `` `COUNTERS_DB` ``, `ASIC_DB`-adjacent uppercase
    tokens are extracted; the table name is matched (loosely, stripping
    trailing `_TABLE`) against existing CDB ref slugs.
  - **chassis / SmartSwitch keyword map**: hardcoded keyword -> CDB/CLI/YANG
    expansion for chassis-state / dpu-state / smartswitch-* / mid-plane,
    which the legacy heuristics tend to miss because these tokens are
    typically not bracketed.
  - **discrepancy-found next-action links**: for pages with
    `verification: discrepancy-found`, parse the `<!-- next-action -->`
    block for `../reference/{cli,config-db,yang}/<slug>.md` links and
    surface those references in `related`.
  - **via-runbook inference**: title / slug token prefix-match against
    runbook ref pages; for each matched runbook, harvest its own
    `related.{cli,config_db,yang}` and add to candidates.

Each list is capped at 7 entries (5 in default mode), ranked by occurrence
frequency.

By default only pages whose `related` is fully empty are touched. With
`--thin-threshold N`, pages where every list has < N entries are also
considered. Existing non-empty fields are never overwritten; new
candidates are *appended* up to the per-list cap.

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
RUNBOOK_REF_DIR = "docs/reference/runbooks"

# Keyword -> {cdb, cli, yang} hardcoded map for chassis / SmartSwitch / DPU
# topic clusters. Entries are only emitted when the corresponding ref page
# actually exists in the repo (validated at runtime).
CHASSIS_KEYWORD_MAP: dict[str, dict[str, list[str]]] = {
    "chassis": {
        "config_db": ["CHASSIS_MODULE", "MID_PLANE_BRIDGE", "DPU"],
        "cli": ["show chassis modules status", "config chassis modules"],
    },
    "chassis-state": {
        "config_db": ["CHASSIS_MODULE", "MID_PLANE_BRIDGE", "DPU"],
        "cli": ["show chassis modules status"],
    },
    "smartswitch": {
        "config_db": ["DPU", "CHASSIS_MODULE", "MID_PLANE_BRIDGE", "DPUS"],
        "cli": ["show chassis modules status", "show platform inventory"],
    },
    "dpu": {
        "config_db": ["DPU", "CHASSIS_MODULE", "MID_PLANE_BRIDGE"],
        "cli": ["show chassis modules status", "show platform inventory"],
    },
    "dpu-state": {
        "config_db": ["DPU", "CHASSIS_MODULE"],
        "cli": ["show chassis modules status"],
    },
    "mid-plane": {
        "config_db": ["MID_PLANE_BRIDGE"],
    },
    "midplane": {
        "config_db": ["MID_PLANE_BRIDGE"],
    },
    "pdu": {
        "config_db": ["DPU", "CHASSIS_MODULE"],
    },
    "voq": {
        "config_db": ["VOQ_INBAND_INTERFACE"],
    },
}

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


def related_is_thin(fm: dict, threshold: int) -> bool:
    """Page qualifies as 'thin': every related list has < threshold entries.

    threshold <= 1 is equivalent to `related_is_empty`.
    """
    rel = fm.get("related") or {}
    if not isinstance(rel, dict):
        return False
    for key in ("cli", "config_db", "yang"):
        v = rel.get(key) or []
        if isinstance(v, list) and len(v) >= threshold:
            return False
    return True


def related_is_partial(fm: dict) -> bool:
    """Page qualifies as 'partial': at least one of cli/config_db/yang is
    empty AND at least one is non-empty. Fully-empty pages are excluded
    (those are handled by `related_is_empty`)."""
    rel = fm.get("related") or {}
    if not isinstance(rel, dict):
        return False
    if fm.get("_no_related") is True:
        return False
    empty_count = 0
    nonempty_count = 0
    for key in ("cli", "config_db", "yang"):
        v = rel.get(key) or []
        if isinstance(v, list) and v:
            nonempty_count += 1
        else:
            empty_count += 1
    return empty_count >= 1 and nonempty_count >= 1


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


def load_runbook_refs(root: Path) -> dict[str, dict[str, list[str]]]:
    """Load runbook ref pages: slug -> {cli, config_db, yang} from frontmatter."""
    out: dict[str, dict[str, list[str]]] = {}
    d = root / RUNBOOK_REF_DIR
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
        if not isinstance(rel, dict):
            continue
        out[f.stem] = {
            "cli": [str(x) for x in (rel.get("cli") or []) if x],
            "config_db": [str(x) for x in (rel.get("config_db") or []) if x],
            "yang": [str(x) for x in (rel.get("yang") or []) if x],
        }
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

# STATE_DB / COUNTERS_DB / ASIC_DB scoped table references such as
# `STATE_DB:CHASSIS_MODULE_TABLE`, ``STATE_DB`` followed by a backticked
# uppercase table name, ASIC_DB:ASIC_STATE etc.
STATE_DB_SCOPED_PAT = re.compile(
    r"\b(STATE_DB|COUNTERS_DB|ASIC_DB|APPL_DB|APP_DB|FLEX_COUNTER_DB)\s*[:`]+\s*([A-Z][A-Z0-9_]{2,})"
)
# Uppercase tables ending in _TABLE, _SET, _LIST that often appear in
# STATE_DB / COUNTERS_DB descriptions.
SCOPED_UPPER_PAT = re.compile(r"\b([A-Z][A-Z0-9_]{3,}(?:_TABLE|_LIST|_SET|_STATE))\b")

# Reference page links inside `next-action` admonitions.
NEXT_ACTION_BLOCK_PAT = re.compile(
    r"<!--\s*next-action\s*-->(.*?)<!--\s*/next-action\s*-->",
    re.S,
)
REF_LINK_PAT = re.compile(
    r"\(\.\.\/reference\/(cli|config-db|yang|runbooks)\/([a-z0-9][a-z0-9\-_]*)\.md(?:#[^)]*)?\)"
)

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


def _cdb_match_with_strip(token: str, cdb_idx: set[str], cdb_slugs: dict[str, str]) -> str | None:
    """Match an uppercase token (possibly with `_TABLE` suffix) to a CDB table.

    Returns the canonical table name if found, else None.
    """
    # 1) direct match
    if token in cdb_idx:
        return token
    # 2) strip common scope suffixes
    for suf in ("_TABLE", "_LIST", "_SET", "_STATE"):
        if token.endswith(suf):
            base = token[: -len(suf)]
            if base in cdb_idx:
                return base
    return None


def extract_state_db(
    body: str, cdb_idx: set[str], cdb_slugs: dict[str, str]
) -> list[str]:
    """Detect STATE_DB / COUNTERS_DB / ASIC_DB scoped table references and
    return CDB table names that match the existing reference index.
    """
    counter: Counter = Counter()
    for m in STATE_DB_SCOPED_PAT.finditer(body):
        tok = m.group(2)
        canon = _cdb_match_with_strip(tok, cdb_idx, cdb_slugs)
        if canon:
            counter[canon] += 1
    # Also catch `_TABLE` / `_STATE` suffix tokens anywhere in body — these
    # are often STATE_DB key prefixes that share base name with a CDB table.
    for m in SCOPED_UPPER_PAT.finditer(body):
        tok = m.group(1)
        canon = _cdb_match_with_strip(tok, cdb_idx, cdb_slugs)
        if canon:
            counter[canon] += 1
    return [k for k, _ in counter.most_common()]


def extract_chassis_keywords(
    body: str,
    fm: dict,
    path: Path,
    cdb_idx: set[str],
    cli_idx: dict[str, str],
    yang_idx: set[str],
) -> tuple[list[str], list[str], list[str]]:
    """Match hardcoded chassis/SmartSwitch/DPU keywords and emit candidates."""
    extra_cli: list[str] = []
    extra_cdb: list[str] = []
    extra_yang: list[str] = []
    title = str(fm.get("title") or "").lower()
    slug = path.stem.lower()
    haystack_meta = f"{title} {slug}"
    # Body-level signals require a clear contextual match (not just any
    # appearance of `dpu`); use a slightly stricter regex.
    body_lc = body.lower()
    for kw, mapping in CHASSIS_KEYWORD_MAP.items():
        if kw in haystack_meta or re.search(rf"\b{re.escape(kw)}\b", body_lc):
            for tbl in mapping.get("config_db", []):
                if tbl not in extra_cdb:
                    extra_cdb.append(tbl)
            for cmd in mapping.get("cli", []):
                if cmd in cli_idx and cmd not in extra_cli:
                    extra_cli.append(cmd)
            for y in mapping.get("yang", []):
                if y in yang_idx and y not in extra_yang:
                    extra_yang.append(y)
    return extra_cli, extra_cdb, extra_yang


def extract_next_action_links(
    body: str,
    fm: dict,
    cli_idx: dict[str, str],
    cli_slugs: dict[str, str],
    cdb_slugs: dict[str, str],
    yang_idx: set[str],
    runbook_refs: dict[str, dict[str, list[str]]],
) -> tuple[list[str], list[str], list[str]]:
    """Parse `<!-- next-action -->` block for `../reference/...` links and
    convert them into CLI / CDB / YANG candidates.

    Only emitted for `discrepancy-found` pages where the next-action block
    is the canonical place to surface alternative references.
    """
    if str(fm.get("verification") or "") != "discrepancy-found":
        return [], [], []
    m = NEXT_ACTION_BLOCK_PAT.search(body)
    if not m:
        return [], [], []
    block = m.group(1)
    cli_out: list[str] = []
    cdb_out: list[str] = []
    yang_out: list[str] = []
    for lm in REF_LINK_PAT.finditer(block):
        kind = lm.group(1)
        slug = lm.group(2)
        if kind == "cli":
            cmd = cli_slugs.get(slug)
            if cmd and cmd not in cli_out:
                cli_out.append(cmd)
        elif kind == "config-db":
            tbl = cdb_slugs.get(slug)
            if tbl and tbl not in cdb_out:
                cdb_out.append(tbl)
        elif kind == "yang":
            if slug in yang_idx and slug not in yang_out:
                yang_out.append(slug)
        elif kind == "runbooks":
            # Harvest the runbook's own related.{cli,cdb,yang}.
            rb = runbook_refs.get(slug)
            if rb:
                for cmd in rb.get("cli", []):
                    if cmd in cli_idx and cmd not in cli_out:
                        cli_out.append(cmd)
                for tbl in rb.get("config_db", []):
                    if tbl not in cdb_out:
                        cdb_out.append(tbl)
                for y in rb.get("yang", []):
                    if y in yang_idx and y not in yang_out:
                        yang_out.append(y)
    return cli_out, cdb_out, yang_out


def extract_via_runbook(
    tokens: list[str],
    cli_idx: dict[str, str],
    yang_idx: set[str],
    runbook_refs: dict[str, dict[str, list[str]]],
) -> tuple[list[str], list[str], list[str]]:
    """For tokens that prefix-match a runbook slug, harvest the runbook's
    own related.{cli,config_db,yang}.
    """
    extra_cli: list[str] = []
    extra_cdb: list[str] = []
    extra_yang: list[str] = []
    if not runbook_refs:
        return extra_cli, extra_cdb, extra_yang
    matched_slugs: list[str] = []
    for tok in tokens:
        for rslug in runbook_refs:
            if rslug == tok or rslug.startswith(tok + "-"):
                if rslug not in matched_slugs:
                    matched_slugs.append(rslug)
    for rslug in matched_slugs:
        rb = runbook_refs[rslug]
        for cmd in rb.get("cli", []):
            if cmd in cli_idx and cmd not in extra_cli:
                extra_cli.append(cmd)
        for tbl in rb.get("config_db", []):
            if tbl not in extra_cdb:
                extra_cdb.append(tbl)
        for y in rb.get("yang", []):
            if y in yang_idx and y not in extra_yang:
                extra_yang.append(y)
    return extra_cli, extra_cdb, extra_yang


def extract_aggressive(
    body: str,
    fm: dict,
    path: Path,
    cli_idx: dict[str, str],
    cli_slugs: dict[str, str],
    cdb_idx: set[str],
    cdb_slugs: dict[str, str],
    yang_idx: set[str],
    cli_to_cdb: dict[str, list[str]],
    runbook_refs: dict[str, dict[str, list[str]]],
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

    # 3. STATE_DB / COUNTERS_DB / ASIC_DB scoped table refs in body.
    for tbl in extract_state_db(body, cdb_idx, cdb_slugs):
        extra_cdb[tbl] += 1

    # 4. chassis / SmartSwitch / DPU keyword map.
    ck_cli, ck_cdb, ck_yang = extract_chassis_keywords(
        body, fm, path, cdb_idx, cli_idx, yang_idx
    )
    for cmd in ck_cli:
        extra_cli[cmd] += 1
    for tbl in ck_cdb:
        extra_cdb[tbl] += 1
    for y in ck_yang:
        extra_yang[y] += 1

    # 5. discrepancy-found next-action back-links.
    na_cli, na_cdb, na_yang = extract_next_action_links(
        body, fm, cli_idx, cli_slugs, cdb_slugs, yang_idx, runbook_refs
    )
    for cmd in na_cli:
        extra_cli[cmd] += 2  # boost: explicit author-curated links
    for tbl in na_cdb:
        extra_cdb[tbl] += 2
    for y in na_yang:
        extra_yang[y] += 2

    # 6. via-runbook inference: token prefix-match against runbook ref slugs.
    rb_cli, rb_cdb, rb_yang = extract_via_runbook(
        uniq_tokens, cli_idx, yang_idx, runbook_refs
    )
    for cmd in rb_cli:
        extra_cli[cmd] += 1
    for tbl in rb_cdb:
        extra_cdb[tbl] += 1
    for y in rb_yang:
        extra_yang[y] += 1

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
    runbook_refs,
    mode: str,
    dry_run: bool,
    thin_threshold: int,
    partial_only: bool = False,
):
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        return None
    if fm.get("_no_related") is True:
        return None
    if partial_only:
        if not related_is_partial(fm):
            return None
    else:
        is_empty = related_is_empty(fm)
        is_thin = thin_threshold > 1 and related_is_thin(fm, thin_threshold)
        if not is_empty and not is_thin:
            return None

    aggressive = mode == "aggressive"
    cap = 7 if aggressive else 5

    cli = extract_cli(body, cli_idx, cap)
    cdb = extract_cdb(body, cdb_idx, cap)
    yng = extract_yang(body, yang_idx, cap)

    if aggressive:
        ex_cli, ex_cdb, ex_yang = extract_aggressive(
            body, fm, path, cli_idx, cli_slugs, cdb_idx, cdb_slugs,
            yang_idx, cli_to_cdb, runbook_refs,
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

    # Preserve existing entries. For thin pages we APPEND new candidates
    # (deduped) up to the per-list cap, never overwriting.
    def _merge_existing(existing: list, new_items: list[str]) -> list[str]:
        existing = [str(x) for x in (existing or []) if x]
        seen = set(existing)
        merged = list(existing)
        for it in new_items:
            if it in seen:
                continue
            if len(merged) >= cap:
                break
            seen.add(it)
            merged.append(it)
        return merged

    new_cli = _merge_existing(rel.get("cli"), cli)
    new_cdb = _merge_existing(rel.get("config_db"), cdb)
    new_yang = _merge_existing(rel.get("yang"), yng)

    # If nothing actually changed, skip the write.
    if (new_cli == (rel.get("cli") or [])
            and new_cdb == (rel.get("config_db") or [])
            and new_yang == (rel.get("yang") or [])):
        return ("noop", path, [], [], [])

    rel["cli"] = new_cli
    rel["config_db"] = new_cdb
    rel["yang"] = new_yang
    fm["related"] = rel

    new_text = "---\n" + dump_frontmatter(fm) + "---\n" + body
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return ("update", path, new_cli, new_cdb, new_yang)


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
    ap.add_argument(
        "--partial-only",
        action="store_true",
        help=(
            "Only process pages where at least one of related.{cli,config_db,yang} "
            "is empty AND at least one is non-empty (fills the gaps; never overwrites)."
        ),
    )
    ap.add_argument(
        "--thin-threshold",
        type=int,
        default=1,
        help=(
            "When > 1, also process pages whose every related list has < N "
            "entries (existing entries are preserved, new candidates appended)."
        ),
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    cli_idx = load_cli_index(root)
    cli_slugs = load_cli_slugs(root)
    cdb_idx = load_cdb_index(root)
    cdb_slugs = load_cdb_slugs(root)
    yang_idx = load_yang_index(root)
    cli_to_cdb = load_cli_to_cdb(root) if args.mode == "aggressive" else {}
    runbook_refs = load_runbook_refs(root) if args.mode == "aggressive" else {}

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
            runbook_refs,
            args.mode,
            args.dry_run,
            args.thin_threshold,
            args.partial_only,
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
