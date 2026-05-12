#!/usr/bin/env python3
"""Build initial indexes for sonic-unofficial-docs."""
from __future__ import annotations
import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/coder/sonic-unofficial-docs")
SRC = ROOT / ".cache" / "sonic-sources"
OUT = ROOT / "meta" / "index"
OUT.mkdir(parents=True, exist_ok=True)

REPOS = [
    "SONiC", "sonic-buildimage", "sonic-utilities", "sonic-swss",
    "sonic-swss-common", "sonic-sairedis", "sonic-mgmt-common",
    "sonic-platform-common", "sonic-platform-daemons", "sonic-snmpagent",
    "sonic-dhcp-relay", "sonic-linkmgrd", "sonic-host-services",
    "sonic-gnmi", "sonic-frr",
]

REPO_DESCRIPTIONS = {
    "SONiC": "SONiC top-level docs and HLDs",
    "sonic-buildimage": "Build infrastructure and Docker images for SONiC",
    "sonic-utilities": "CLI utilities (config, show, clear, sonic-installer, etc.)",
    "sonic-swss": "Switch State Service - orchestration agents (orchagent, etc.)",
    "sonic-swss-common": "Common library for SWSS (DB clients, schema)",
    "sonic-sairedis": "SAI redis adapter (syncd) and SAI infrastructure",
    "sonic-mgmt-common": "Management framework common code (translib, transformer)",
    "sonic-platform-common": "Platform abstraction APIs and base classes",
    "sonic-platform-daemons": "Platform daemons (xcvrd, pcied, psud, ledd, thermalctld, etc.)",
    "sonic-snmpagent": "SNMP subagent for SONiC",
    "sonic-dhcp-relay": "DHCP relay agent for SONiC",
    "sonic-linkmgrd": "Dual-ToR link manager daemon",
    "sonic-host-services": "Host-side services (hostcfgd, procdockerstatsd, etc.)",
    "sonic-gnmi": "gNMI/gNOI server for SONiC",
    "sonic-frr": "FRRouting fork/integration for SONiC",
}

# ----- Utilities -----

def sh(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd) if cwd else None, text=True).strip()

def head_sha(repo_path: Path) -> str:
    try:
        return sh(["git", "rev-parse", "HEAD"], cwd=repo_path)
    except Exception:
        return ""

def default_branch(repo_path: Path) -> str:
    try:
        out = sh(["git", "symbolic-ref", "--short", "HEAD"], cwd=repo_path)
        return out
    except Exception:
        try:
            return sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        except Exception:
            return "master"

EXCLUDED_NAMES = {"README.md", "readme.md", "Readme.md", "CONTRIBUTING.md",
                  "LICENSE.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
                  "CHANGELOG.md", "CHANGES.md"}

DOC_DIRS = ("doc", "docs", "Documentation")

# Noise slugs derived from generic HLD H2 section names. Any backlog /
# page slug matching this pattern is a structural fragment, not a feature
# page, and should be skipped at backlog-generation time.
NOISE_SLUG_RE = re.compile(
    r"^("
    r"introduction"
    r"|overview"
    r"|summary"
    r"|abstract"
    r"|background"
    r"|scope"
    r"|references"
    r"|appendix"
    r"|revision"
    r"|requirements"
    r"|definitions"
    r"|definitions-abbreviations"
    r"|abbreviations"
    r"|terminology"
    r"|table-of-contents"
    r"|toc"
    r"|conclusion"
    r"|feature-name"
    r"|hld-name"
    r")(-\d+)?$"
)


def is_noise_slug(slug: str) -> bool:
    """Return True if `slug` is a generic HLD section fragment that
    should be filtered out from indexes and backlogs."""
    if not slug:
        return True
    return bool(NOISE_SLUG_RE.match(slug.strip().lower()))


# Minimum useful HLD payload size. HLDs below this are usually stubs,
# "in_progress" placeholders, or single-line redirects.
HLD_MIN_SIZE_BYTES = 500


def _slug_from_path(path: str) -> str:
    """Derive a normalised slug from a doc file path (stem only)."""
    name = path.rsplit("/", 1)[-1]
    if name.lower().endswith(".md"):
        name = name[:-3]
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def is_low_quality_hld(entry: dict) -> tuple[bool, str]:
    """Return (drop, reason) for an HLD index entry.

    Drops entries whose filename slug matches the generic HLD section
    noise pattern (introduction-N, revision, appendix-X, etc.) or whose
    payload is below HLD_MIN_SIZE_BYTES (stub / placeholder files).
    """
    slug = _slug_from_path(entry.get("path", ""))
    if is_noise_slug(slug):
        return True, f"noise-slug ({slug})"
    size = int(entry.get("size_bytes") or 0)
    if size < HLD_MIN_SIZE_BYTES:
        return True, f"stub ({size}B < {HLD_MIN_SIZE_BYTES}B)"
    return False, ""

AREA_KEYWORDS = [
    ("routing", ["bgp", "ospf", "isis", "route", "frr", "vrf", "static-route",
                 "rip", "fpm", "ecmp", "bfd", "nexthop", "prefix-list", "routemap",
                 "srv6", "mpls", "ldp", "evpn"]),
    ("overlay", ["vxlan", "vnet", "evpn", "tunnel", "overlay", "geneve", "nvgre"]),
    ("switching", ["vlan", "stp", "lldp", "lag", "lacp", "portchannel", "fdb",
                   "mac", "switching", "spanning-tree", "mclag", "l2"]),
    ("acl-qos", ["acl", "qos", "scheduler", "wred", "buffer", "pfc", "ecn",
                 "policer", "shaper", "queue", "priority", "dscp", "tc-to-",
                 "copp", "mirror"]),
    ("system", ["syslog", "ntp", "snmp", "logging", "auto_techsupport",
                "techsupport", "kdump", "warmboot", "warm-boot", "fastboot",
                "fast-boot", "reboot", "telemetry", "system-health",
                "auto-techsupport", "memory", "watchdog", "service",
                "image", "installer", "upgrade", "feature", "container",
                "supervisor", "monit"]),
    ("management", ["gnmi", "gnoi", "rest", "netconf", "mgmt", "management",
                    "yang", "translib", "ssh", "tacacs", "radius", "aaa",
                    "console", "dhcp_server", "dhcp-server", "config-cli",
                    "cli", "click"]),
    ("platform", ["platform", "sfp", "transceiver", "xcvr", "psu", "fan",
                  "thermal", "led", "fpga", "cpld", "pcie", "chassis",
                  "linecard", "asic", "sai", "syncd", "pmon", "sensor",
                  "gearbox"]),
    ("internals", ["orchagent", "swss", "syncd", "redis", "appl_db", "asic_db",
                   "config_db", "state_db", "counters_db", "schema",
                   "saibcm", "fdb-internals", "internal", "hld-internals"]),
    ("architecture", ["architecture", "design", "overview", "framework",
                      "infrastructure", "high-level"]),
]

def guess_area(path: str, title: str) -> str:
    s = (path + " " + (title or "")).lower()
    for area, kws in AREA_KEYWORDS:
        for kw in kws:
            if kw in s:
                return area
    return "unknown"

def extract_h1(file_path: Path, max_bytes: int = 200_000) -> str:
    try:
        size = file_path.stat().st_size
        if size > 1_000_000:
            return ""
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            for _ in range(200):
                line = f.readline()
                if not line:
                    break
                m = re.match(r"^\s*#\s+(.+?)\s*#*\s*$", line)
                if m:
                    return m.group(1).strip()
                # setext-style
                # skip
    except Exception:
        pass
    return ""

# ----- HLD index -----

def build_hld() -> list[dict]:
    entries = []
    dropped: list[tuple[str, str]] = []
    for repo in REPOS:
        repo_path = SRC / repo
        if not repo_path.exists():
            continue
        sha = head_sha(repo_path)
        candidates: set[Path] = set()
        for d in DOC_DIRS:
            top = repo_path / d
            if top.exists() and top.is_dir():
                for p in top.rglob("*.md"):
                    candidates.add(p)
        for p in sorted(candidates):
            if p.name in EXCLUDED_NAMES:
                continue
            rel = p.relative_to(repo_path).as_posix()
            try:
                size = p.stat().st_size
            except OSError:
                continue
            title = extract_h1(p)
            area = guess_area(rel, title)
            cand = {
                "repo": f"sonic-net/{repo}",
                "path": rel,
                "ref": sha,
                "title": title,
                "area_hint": area,
                "size_bytes": size,
            }
            drop, reason = is_low_quality_hld(cand)
            if drop:
                dropped.append((f"{repo}/{rel}", reason))
                continue
            entries.append(cand)
    if dropped:
        print(f"[hld] filtered {len(dropped)} low-quality entries:",
              file=sys.stderr)
        for path, reason in dropped:
            print(f"  - {path}: {reason}", file=sys.stderr)
    return entries

# ----- CLI index -----

CLI_TARGETS = [
    ("sonic-utilities", "config/main.py"),
    ("sonic-utilities", "show/main.py"),
    ("sonic-utilities", "clear/main.py"),
]

class ClickVisitor(ast.NodeVisitor):
    """Best-effort extraction of click commands/groups from a single file.

    Builds a map from variable name -> ('group'|'command', help_str, parent_var_or_None).
    """
    def __init__(self):
        # name -> {kind, help, parent}
        self.nodes: dict[str, dict] = {}

    def _decorator_info(self, deco):
        # Returns (parent_var, kind) or (None, None)
        # forms:
        #   @click.command(...)
        #   @click.group(...)
        #   @<var>.command(...)
        #   @<var>.group(...)
        if isinstance(deco, ast.Call):
            func = deco.func
        else:
            func = deco
        kind = None
        parent = None
        if isinstance(func, ast.Attribute):
            attr = func.attr
            if attr in ("command", "group"):
                kind = attr
                val = func.value
                if isinstance(val, ast.Name):
                    parent = val.id  # could be 'click' or a group var
                elif isinstance(val, ast.Attribute):
                    parent = None
        return parent, kind

    def _extract_help(self, deco) -> str:
        if not isinstance(deco, ast.Call):
            return ""
        for kw in deco.keywords:
            if kw.arg == "help" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value.strip().splitlines()[0][:300] if kw.value.value else ""
        # short_help
        for kw in deco.keywords:
            if kw.arg == "short_help" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value.strip()[:300]
        return ""

    def _extract_name(self, deco, func_name: str) -> str:
        if isinstance(deco, ast.Call):
            # first positional arg is name in click
            if deco.args and isinstance(deco.args[0], ast.Constant) and isinstance(deco.args[0].value, str):
                return deco.args[0].value
            for kw in deco.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    return kw.value.value
        # default: function name with underscores -> hyphens (click default keeps underscores actually,
        # but sonic-utilities tends to use hyphens; we keep function name)
        return func_name.replace("_", "-")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for deco in node.decorator_list:
            parent, kind = self._decorator_info(deco)
            if kind is None:
                continue
            name = self._extract_name(deco, node.name)
            help_str = self._extract_help(deco)
            self.nodes[node.name] = {
                "kind": kind,
                "name": name,
                "help": help_str,
                "parent": parent,  # variable name of parent group, or 'click', or None
            }
            break
        self.generic_visit(node)

def build_cli() -> list[dict]:
    entries = []
    for repo, rel in CLI_TARGETS:
        repo_path = SRC / repo
        target = repo_path / rel
        if not target.exists():
            continue
        sha = head_sha(repo_path)
        try:
            tree = ast.parse(target.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        v = ClickVisitor()
        v.visit(tree)
        # Build a tree: walk each node, build path by following parents
        # parent var name == function name of parent group (since click groups are usually defined as `def config(...)` then used as `@config.command(...)`)
        nodes = v.nodes
        # synthesize root name from filename: 'config', 'show', 'clear'
        root_kind = Path(rel).parent.name  # config / show / clear

        for fn_name, info in nodes.items():
            path_parts = []
            cur = fn_name
            seen = set()
            while cur and cur not in seen:
                seen.add(cur)
                cur_info = nodes.get(cur)
                if not cur_info:
                    break
                path_parts.append(cur_info["name"])
                parent = cur_info["parent"]
                if parent in (None, "click"):
                    break
                cur = parent
            path_parts.reverse()
            # prepend root if first element isn't already root_kind
            if not path_parts:
                continue
            if path_parts[0] != root_kind:
                path_parts = [root_kind] + path_parts
            entries.append({
                "command_path": path_parts,
                "kind": info["kind"],
                "help": info["help"],
                "source": {
                    "repo": f"sonic-net/{repo}",
                    "path": rel,
                    "ref": sha,
                },
            })
    # de-dup by command_path string
    seen_paths = set()
    uniq = []
    for e in entries:
        key = (" ".join(e["command_path"]), e["source"]["path"])
        if key in seen_paths:
            continue
        seen_paths.add(key)
        uniq.append(e)
    uniq.sort(key=lambda x: (x["source"]["path"], x["command_path"]))
    return uniq

# ----- YANG index -----

YANG_DIR_REL = "src/sonic-yang-models/yang-models"

YANG_MODULE_RE = re.compile(r'^\s*module\s+([\w\-]+)\s*\{', re.M)
YANG_NS_RE = re.compile(r'namespace\s+"([^"]+)"')
YANG_REV_RE = re.compile(r'revision\s+"?([\d\-]+)"?')
# Top-level container: a 'container <name>' that is at top brace depth 1.

def parse_yang(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    m = YANG_MODULE_RE.search(text)
    if not m:
        return None
    module = m.group(1)
    ns = YANG_NS_RE.search(text)
    rev = YANG_REV_RE.search(text)
    # Find top-level containers: scan with depth tracking
    top_containers = []
    depth = 0
    in_module = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '{':
            depth += 1
            i += 1
            continue
        if ch == '}':
            depth -= 1
            i += 1
            continue
        # at module body depth == 1
        if depth == 1:
            mc = re.match(r'\s*container\s+([\w\-]+)', text[i:])
            if mc:
                top_containers.append(mc.group(1))
                i += mc.end()
                continue
        i += 1
    # de-dup while preserving order
    seen = set()
    uniq_containers = []
    for c in top_containers:
        if c not in seen:
            seen.add(c)
            uniq_containers.append(c)
    return {
        "module": module,
        "revision": rev.group(1) if rev else "",
        "namespace": ns.group(1) if ns else "",
        "top_containers": uniq_containers,
    }

def build_yang() -> list[dict]:
    entries = []
    repo_path = SRC / "sonic-buildimage"
    yang_dir = repo_path / YANG_DIR_REL
    if not yang_dir.exists():
        return entries
    sha = head_sha(repo_path)
    for p in sorted(yang_dir.glob("*.yang")):
        info = parse_yang(p)
        if not info:
            continue
        info["path"] = p.relative_to(repo_path).as_posix()
        info["ref"] = sha
        info["repo"] = "sonic-net/sonic-buildimage"
        entries.append(info)
    return entries

# ----- Repos index -----

def build_repos() -> list[dict]:
    out = []
    for repo in REPOS:
        repo_path = SRC / repo
        out.append({
            "repo": f"sonic-net/{repo}",
            "ref": head_sha(repo_path),
            "default_branch": default_branch(repo_path),
            "description": REPO_DESCRIPTIONS.get(repo, ""),
            "included": True,
        })
    return out

# ----- Main -----

def write_json(path: Path, obj):
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")

def main():
    hld = build_hld()
    cli = build_cli()
    yang = build_yang()
    repos = build_repos()

    write_json(OUT / "hld.json", hld)
    write_json(OUT / "cli.json", cli)
    write_json(OUT / "yang.json", yang)
    write_json(OUT / "repos.json", repos)

    meta = {
        "indexed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool_versions": {
            "python": sys.version.split()[0],
            "indexer_script": "0.1.0",
        },
        "scope": ["master only", "community only"],
        "counts": {
            "hld": len(hld),
            "cli": len(cli),
            "yang": len(yang),
            "repos": len(repos),
        },
    }
    write_json(OUT / "_meta.json", meta)

    print(json.dumps(meta["counts"], indent=2))

if __name__ == "__main__":
    main()
