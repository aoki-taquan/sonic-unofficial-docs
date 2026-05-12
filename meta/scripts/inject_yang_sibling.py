#!/usr/bin/env python3
"""Inject a `<!-- yang-sibling -->` block listing related (sibling) YANG modules
into each `docs/reference/yang/sonic-*.md` page.

Sibling resolution priority:
  1. frontmatter `related.yang` (authoritative manual hints)
  2. a curated GROUP dictionary (semantic clusters: bgp, buffer, vlan, vrf, etc.)
  3. slug prefix sharing (split on `-`, share the first 1-2 tokens)

Up to 5 siblings are emitted, each linked relative to the current page. The
block is idempotent: re-running rewrites the same content if nothing has
changed.

Usage:
    .venv/bin/python3 meta/scripts/inject_yang_sibling.py
    .venv/bin/python3 meta/scripts/inject_yang_sibling.py --check
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"PyYAML required: {exc}", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
YANG_DIR = DOCS / "reference" / "yang"

BEGIN = "<!-- yang-sibling -->"
END = "<!-- /yang-sibling -->"

MAX_SIBLINGS = 5

# Curated semantic clusters. Each set lists slugs (without `.md`) that are
# meaningfully related beyond simple prefix matching.
GROUPS: list[set[str]] = [
    # BGP family
    {
        "sonic-bgp-global", "sonic-bgp-neighbor", "sonic-bgp-peergroup",
        "sonic-bgp-peerrange", "sonic-bgp-aggregate-address",
        "sonic-bgp-device-global", "sonic-bgp-monitor", "sonic-bgp-bbr",
        "sonic-bgp-sentinel", "sonic-route-map", "sonic-route-common",
        "sonic-bmp",
    },
    # VRF / routing core
    {
        "sonic-vrf", "sonic-mgmt_vrf", "sonic-static-route",
        "sonic-route-map", "sonic-route-common", "sonic-bgp-global",
        "sonic-interface", "sonic-loopback-interface",
    },
    # Interface / port / portchannel
    {
        "sonic-port", "sonic-portchannel", "sonic-interface",
        "sonic-vlan", "sonic-vlan-sub-interface", "sonic-loopback-interface",
        "sonic-mgmt_port", "sonic-mgmt_interface", "sonic-breakout_cfg",
        "sonic-fabric-port",
    },
    # VLAN / L2
    {
        "sonic-vlan", "sonic-vlan-sub-interface", "sonic-portchannel",
        "sonic-port", "sonic-spanning-tree", "sonic-storm-control",
        "sonic-mclag",
    },
    # QoS / buffer / scheduler
    {
        "sonic-buffer-pool", "sonic-buffer-profile", "sonic-buffer-pg",
        "sonic-buffer-queue", "sonic-queue", "sonic-scheduler",
        "sonic-wred-profile", "sonic-port-qos-map",
        "sonic-tc-priority-group-map", "sonic-tc-queue-map",
        "sonic-dot1p-tc-map", "sonic-dscp-tc-map",
        "sonic-pfc-priority-priority-group-map",
        "sonic-pfc-priority-queue-map", "sonic-pfcwd",
    },
    # ACL / CoPP / mirror
    {
        "sonic-copp", "sonic-mirror-session", "sonic-pbh",
        "sonic-debug-counter",
    },
    # Tunnels / overlay
    {
        "sonic-vxlan", "sonic-vnet", "sonic-tunnel", "sonic-nvgre-tunnel",
        "sonic-mux-cable", "sonic-srv6",
    },
    # NAT / DHCP / DNS
    {
        "sonic-nat", "sonic-dhcp-server", "sonic-dns", "sonic-neigh",
        "sonic-interface",
    },
    # System / mgmt / AAA
    {
        "sonic-system-aaa", "sonic-system-ldap", "sonic-system-radius",
        "sonic-system-tacacs", "sonic-system-defaults", "sonic-passw-hardening",
        "sonic-snmp", "sonic-syslog", "sonic-ntp", "sonic-lldp",
        "sonic-ssh-server", "sonic-restapi", "sonic-mgmt_interface",
        "sonic-mgmt_port", "sonic-mgmt_vrf", "sonic-feature",
        "sonic-versions", "sonic-banner", "sonic-kdump",
        "sonic-warm-restart", "sonic-device_metadata", "sonic-fips",
    },
    # Counters / monitoring
    {
        "sonic-crm", "sonic-flex_counter", "sonic-debug-counter",
        "sonic-sflow", "sonic-fabric-monitor", "sonic-bgp-monitor",
    },
    # Security / MACsec
    {
        "sonic-macsec", "sonic-port", "sonic-passw-hardening",
        "sonic-system-aaa",
    },
    # ECMP / hash / trimming
    {
        "sonic-fine-grained-ecmp", "sonic-hash", "sonic-trimming",
        "sonic-route-common",
    },
]


def slug_of(path: Path) -> str:
    return path.stem


def page_set() -> set[str]:
    return {slug_of(p) for p in YANG_DIR.glob("sonic-*.md")}


def from_frontmatter(fm: dict) -> list[str]:
    related = (fm or {}).get("related") or {}
    return [str(x).strip().lower() for x in (related.get("yang") or [])]


def from_groups(slug: str, present: set[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for grp in GROUPS:
        if slug in grp:
            for s in sorted(grp):
                if s != slug and s in present and s not in seen:
                    out.append(s)
                    seen.add(s)
    return out


def from_prefix(slug: str, present: set[str]) -> list[str]:
    parts = slug.split("-")
    if len(parts) < 2:
        return []
    # Use first 2 tokens for richer signal (e.g. "sonic-bgp"), but also
    # fall back to first 3 tokens for things like "sonic-pfc-priority-*".
    out: list[str] = []
    seen: set[str] = set()
    for take in (3, 2):
        if len(parts) < take + 1:
            continue
        prefix = "-".join(parts[:take]) + "-"
        for s in sorted(present):
            if s == slug or s in seen:
                continue
            if s.startswith(prefix):
                out.append(s)
                seen.add(s)
    return out


def resolve_siblings(slug: str, fm: dict, present: set[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def add_all(items: list[str]) -> None:
        for s in items:
            if s == slug or s not in present or s in seen:
                continue
            seen.add(s)
            ordered.append(s)

    add_all(from_frontmatter(fm))
    add_all(from_groups(slug, present))
    add_all(from_prefix(slug, present))
    return ordered[:MAX_SIBLINGS]


def build_block(slug: str, siblings: list[str]) -> str:
    if not siblings:
        return ""
    items = "\n".join(
        f"- [`{s}`]({s}.md)" for s in siblings
    )
    inner = (
        "### 関連 YANG モジュール\n\n"
        "意味的に関連する SONiC YANG モジュール (slug prefix / curated group / "
        "frontmatter `related.yang` から自動抽出):\n\n"
        f"{items}\n"
    )
    return f"{BEGIN}\n{inner}{END}"


EXISTING_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)

# Anchor candidates for placement (insert before the earliest one).
ANCHOR_PATTERNS = [
    re.compile(r"^<!-- ref-triangle:start -->\s*$", re.MULTILINE),
    re.compile(r"^## 関連リファレンス\s*$", re.MULTILINE),
    re.compile(r"^<!-- ops-hint -->\s*$", re.MULTILINE),
    re.compile(r"^## 運用ヒント\s*$", re.MULTILINE),
    re.compile(r"^## 引用元\s*$", re.MULTILINE),
    re.compile(r"^<!-- glossary-links-injected:[^>]*-->\s*$", re.MULTILINE),
]


def inject(body: str, block: str) -> str:
    if not block:
        # Remove any stale block if siblings became empty.
        if EXISTING_RE.search(body):
            return EXISTING_RE.sub("", body).rstrip() + "\n"
        return body
    if EXISTING_RE.search(body):
        return EXISTING_RE.sub(lambda _m: block, body, count=1)
    anchors: list[int] = []
    for pat in ANCHOR_PATTERNS:
        m = pat.search(body)
        if m:
            anchors.append(m.start())
    if anchors:
        idx = min(anchors)
        before = body[:idx].rstrip() + "\n\n"
        after = body[idx:]
        return before + block + "\n\n" + after
    return body.rstrip() + "\n\n" + block + "\n"


def parse_page(path: Path) -> Optional[tuple[dict, str, str]]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    return fm, m.group(1), m.group(2)


def process(check: bool) -> int:
    present = page_set()
    pages = sorted(YANG_DIR.glob("sonic-*.md"))
    touched = 0
    drift = 0
    with_siblings = 0
    for path in pages:
        parsed = parse_page(path)
        if parsed is None:
            continue
        fm, fm_text, body = parsed
        slug = slug_of(path)
        siblings = resolve_siblings(slug, fm, present)
        if siblings:
            with_siblings += 1
        block = build_block(slug, siblings)
        new_body = inject(body, block)
        if new_body == body:
            continue
        drift += 1
        if check:
            print(f"would-update: {path.relative_to(ROOT)} (siblings={len(siblings)})")
        else:
            path.write_text(f"---\n{fm_text}\n---\n{new_body}", encoding="utf-8")
            touched += 1
            print(f"updated: {path.relative_to(ROOT)} (siblings={len(siblings)})")

    total = len(pages)
    if check:
        print(f"\n[check] yang pages: {total}, with-siblings: {with_siblings}, drift: {drift}")
        return 1 if drift else 0
    print(f"\n[write] yang pages: {total}, with-siblings: {with_siblings}, updated: {touched}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument("--check", action="store_true", help="dry-run; exit non-zero if drift")
    args = ap.parse_args()
    return process(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
