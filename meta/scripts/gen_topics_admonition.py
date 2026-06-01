#!/usr/bin/env python3
"""HLD 派生ページ冒頭に Topics 章への誘導 admonition を挿入する。

対応する Topics 章がある HLD ページに対し、frontmatter 直後（既存の最初の
admonition の前）に以下を挿入する:

    <!-- topics-tip -->
    !!! tip "Topics で読み物として読む"
        この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として
        読みたい場合は [Topics XX 章: TITLE](../../topics/XX-name/) を参照。
    <!-- /topics-tip -->

マーカー `<!-- topics-tip -->` が既にある場合はスキップ（再実行安全）。

マッピング: 各 Topics 章番号と area 単位のキーワード (slug substring) で対応付ける。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

MARK_START = "<!-- topics-tip -->"
MARK_END = "<!-- /topics-tip -->"

FRONTMATTER_RE = re.compile(r"^(---\n.*?\n---\n)", re.DOTALL)

# (chapter_num, chapter_dir, title, [ (area, [slug-substrings]) ... ])
# slug substring match: 全部の substring が slug に出てきたら一致 (AND)
# 1 つの substring が含まれれば OK（OR）で扱う。
TOPIC_MAP: list[tuple[str, str, str, list[tuple[str, list[str]]]]] = [
    (
        "02",
        "02-bgp",
        "BGP と FRR 制御プレーン",
        [
            ("routing", [
                "bgp", "frr", "fpmsyncd", "bmp-for-monitoring",
                "ciscobgp4mib", "default-route", "ipv6-link-local",
                "bfd-hw-offload",
            ]),
        ],
    ),
    (
        "03",
        "03-vxlan-evpn",
        "VXLAN / EVPN とオーバーレイ",
        [
            ("routing", ["evpn-vxlan", "overlay-ecmp"]),
            ("overlay", ["vxlan", "nvgre", "vnet"]),
        ],
    ),
    (
        "04",
        "04-vrf-ecmp",
        "VRF / ECMP / 経路選択",
        [
            ("routing", [
                "vrf", "ecmp", "nexthop", "multiple-nexthop",
                "routing-and-next-hop", "fine-grained-ecmp",
                "weighted-ecmp", "local-ars", "static-ip-route",
                "class-based-forwarding", "route-flow-counter",
                "router-interface-counters", "mpls",
                "segment-routing", "srv6", "usid",
                "virtual-router-redundancy",
            ]),
        ],
    ),
    (
        "05",
        "05-dual-tor",
        "Dual ToR / MUX / アクティブ冗長",
        [
            ("overlay", ["dual-tor", "dscp-remapping"]),
            ("routing", ["prefix-based-mux", "reliable-tsa"]),
        ],
    ),
    (
        "06",
        "06-l2-vlan-lag",
        "L2 / VLAN / LAG",
        [
            ("switching", [
                "vlan", "lag", "lacp", "layer-2", "mclag",
                "iccp", "spanning-tree", "portchannel",
                "bum-storm", "wake-on-lan", "macsec",
                "ip-lag", "link-event", "switch-port",
                "system-defaults",
            ]),
        ],
    ),
    (
        "07",
        "07-acl-copp-mirror",
        "ACL / CoPP / Mirror",
        [
            ("acl-qos", [
                "acl", "copp", "mirror", "everflow", "dash-acl",
                "dhcp-dos", "port-access-control",
                "configurable-drop-counters",
                "egress-mirroring",
                "ingress-discards",
            ]),
        ],
    ),
    (
        "08",
        "08-qos-buffer",
        "QoS / Buffer / PFC",
        [
            ("acl-qos", [
                "qos", "buffer", "pfc", "watermark", "wred",
                "scheduler", "headroom",
                "reclaim-reserved",
                "egress-outer-dscp",
                "port-buffer-drop",
            ]),
        ],
    ),
    (
        "09",
        "09-telemetry-snmp",
        "Telemetry / SNMP / ログ",
        [
            ("system", [
                "snmp", "telemetry", "memory-statistics",
                "persistent-log", "show-techsupport",
                "techsupport", "entity-mib",
                "process-and-docker-stats",
                "reboot-cause",
                "dataplane-telemetry",
                "kdump",
                "dump-sfp",
            ]),
            ("internals", [
                "byte-packet-rates", "flexcounter",
                "counter-initialization", "voq-counters",
            ]),
            ("architecture", ["sflow", "bulk-counter", "trap-flow-counter"]),
        ],
    ),
    (
        "10",
        "10-gnmi-openconfig",
        "gNMI / OpenConfig / 管理プレーン",
        [
            ("management", [
                "gnmi", "gnoi", "gnsi", "openconfig",
                "p4rt", "pins", "management-framework",
                "yang", "json-patch", "save-on-set",
                "send-to-ingress", "redis-client-manager",
                "model-based-replace",
                "config-update-validation",
                "nos-configuration",
                "sonic-cli-auto-generation",
                "config-reload-enhancement",
                "packetio",
            ]),
            ("routing", ["gnmi-subscription"]),
            ("switching", ["openconfig-support"]),
        ],
    ),
    (
        "11",
        "11-reboot",
        "Reboot / Warm/Fast/Express/Cold",
        [
            ("system", [
                "fast-reboot", "warm-reboot", "express-reboot",
                "reboot-support",
                "smart-switch-reboot",
                "independent-dpu-upgrade",
                "secure-upgrade",
                "secure-boot",
                "boot-chart",
                "configuration-setup",
                "container-hardening",
            ]),
            ("switching", ["increasing-lacp-pdu-timeout"]),
        ],
    ),
    (
        "12",
        "12-multi-asic-voq",
        "Multi-ASIC / VoQ / Chassis",
        [
            ("platform", [
                "multi-asic", "voq-chassis", "voq-sonic",
                "single-asic-voq", "fabric-port",
                "recirculation-port",
                "db-design-for-multi-asic",
                "multi-asic-single-json",
            ]),
            ("internals", ["voq-counters", "l3-scaling"]),
            ("system", ["multi-asic-warm-reboot", "platform-monitor-design-for-multi-asic"]),
            ("routing", ["voq-chassis"]),
            ("switching", ["distributed-voq"]),
            ("acl-qos", ["virtual-output-queue", "voq"]),
        ],
    ),
    (
        "13",
        "13-dash-smartswitch",
        "DASH / SmartSwitch",
        [
            ("overlay", ["dash", "smartswitch", "eni"]),
            ("system", ["smart-switch", "smartswitch", "dpu"]),
            ("platform", ["smartswitch", "dpu"]),
            ("architecture", ["smart-switch", "smartswitch"]),
            ("management", ["smart-switch", "smartswitch"]),
            ("acl-qos", ["dash"]),
        ],
    ),
    (
        "14",
        "14-platform-port-optics",
        "Platform / Port / Optics",
        [
            ("platform", [
                "cmis", "sfp", "gearbox", "thermal", "psu",
                "port-fec", "port-naming", "fec-flr",
                "media-based-port", "dynamic-port",
                "pcieinfo", "platform-capability",
                "1-6t", "automatic-module",
                "liquid-cooling", "lpo",
                "fast-link-up", "fw-utility",
                "npu-mdio", "tpidsetting",
                "subnet-decapsulation",
                "bmc-flows",
                "icmp-hardware-offload",
                "everflow-support-on-voq",
                "handle-asic-sdk-health",
                "sai-failure", "sai-api-version",
                "query-stats-capability",
                "global-platform-specific",
                "s3ip-sysfs",
                "sfputil",
                "dump-on-sai-failure",
                "enhanced-lpo",
            ]),
            ("system", [
                "thermal", "platform-monitor",
                "bmc-platform", "snmp-transceiver",
                "smart-switch-ip-address",
                "dynamic-port-breakout",
                "asic-thermal",
            ]),
            ("architecture", [
                "port-profile-init", "port-illegal-packets",
                "port-auto-fec", "port-auto-negotiation",
                "port-configuration-refactor",
                "port-link-training",
                "sub-port-interface",
                "udev-rules",
                "clock-managment",
                "s3ip-sysfs",
                "dhcpv4-relay-agent", "dhcpv6-relay-agent",
            ]),
        ],
    ),
    (
        "15",
        "15-security-aaa",
        "Security / AAA",
        [
            ("management", [
                "aaa", "tacacs", "radius", "ldap",
                "default-credential",
                "ssh-server", "serial-console",
                "console-switch", "portable-console",
            ]),
            ("system", [
                "secure-boot", "secure-upgrade",
                "reset-local-users",
                "banner-messages",
                "container-hardening",
            ]),
            ("architecture", ["pw-hardening", "reset-factory"]),
        ],
    ),
    (
        "16",
        "16-nat-dhcp-dns",
        "NAT / DHCP / DNS",
        [
            ("management", [
                "dhcp-relay", "dhcp-server",
            ]),
            ("routing", ["dhcp-relay"]),
            ("architecture", ["nat-in-sonic", "dhcpv4-relay", "dhcpv6-relay"]),
            ("acl-qos", ["dhcp-dos"]),
        ],
    ),
    (
        "17",
        "17-srv6-mpls",
        "SRv6 / MPLS / Segment Routing",
        [
            ("routing", [
                "srv6", "mpls", "segment-routing", "usid",
                "sid-l3adj",
            ]),
        ],
    ),
    (
        "18",
        "18-p4-pins",
        "P4 / PINS",
        [
            ("management", ["p4rt", "pins"]),
            ("internals", ["p4-orchagent"]),
            ("routing", ["path-tracing"]),
        ],
    ),
    (
        "19",
        "19-build-packaging",
        "Build / Packaging / Debian",
        [
            ("architecture", [
                "build-profiles", "build-system",
                "alpine-high-level",
                "rfs-split-build",
                "application-extension",
                "arm-architecture",
            ]),
            ("system", [
                "debian-upgrade",
            ]),
            ("management", [
                "application-extension",
            ]),
        ],
    ),
    (
        "20",
        "20-swss-sai-redis",
        "SWSS / SAI / Redis",
        [
            ("internals", [
                "swss-schema", "redis", "zmq-producer",
                "user-defined-redis", "namespaces",
                "flexcounter", "counter-initialization",
                "dump-utility", "health-check",
            ]),
            ("architecture", [
                "json-change-application",
                "bulk-counter", "generic-hash",
                "generic-configuration-update",
                "trap-flow-counter",
                "ip-interface-loopback",
                "policy-based-hashing",
                "packet-trimming",
                "error-handling",
                "debug-framework",
                "application-extension",
                "sub-port-interface",
            ]),
            ("switching", [
                "producerstatetable",
                "sai-post-support",
            ]),
            ("system", [
                "generic-sai-extension",
            ]),
            ("platform", [
                "sai-api-version", "sai-failure",
                "dump-on-sai-failure",
                "query-stats-capability",
            ]),
        ],
    ),
    (
        "21",
        "21-lab-vs-developer",
        "Lab / SONiC-VS / 開発者",
        [
            ("overlay", ["dash-sonic-kvm"]),
            ("architecture", [
                "sonic-on-gns3",
                "steps-to-bring-up-sonic-vs",
                "dip-sip-ptf-validation",
            ]),
            ("routing", ["vrf-vs-test-plan"]),
        ],
    ),
]

# slug -> (chapter_num, chapter_dir, title) lookup を構築
def build_lookup() -> dict[tuple[str, str], tuple[str, str, str]]:
    lookup: dict[tuple[str, str], tuple[str, str, str]] = {}
    for area_dir in DOCS_DIR.iterdir():
        if not area_dir.is_dir() or area_dir.name in ("topics", "_meta", "categories", "reference", "guides"):
            continue
        area = area_dir.name
        for md in area_dir.glob("*.md"):
            slug = md.stem
            if slug == "index":
                continue
            # 各 topic chapter の中で一致するもの（最初に一致したもの）を採用
            for chap_num, chap_dir, chap_title, areas in TOPIC_MAP:
                for a, substrings in areas:
                    if a != area:
                        continue
                    if any(s in slug for s in substrings):
                        if (area, slug) not in lookup:
                            lookup[(area, slug)] = (chap_num, chap_dir, chap_title)
                        break
    return lookup


def build_admonition(chap_num: str, chap_dir: str, chap_title: str) -> str:
    return (
        f"{MARK_START}\n"
        f"!!! tip \"Topics で読み物として読む\"\n"
        f"    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は "
        f"[Topics {chap_num} 章: {chap_title}](../topics/{chap_dir}/index.md) を参照。\n"
        f"{MARK_END}\n"
    )


def process_file(md: Path, chap_num: str, chap_dir: str, chap_title: str) -> bool:
    text = md.read_text(encoding="utf-8")
    if MARK_START in text:
        return False
    m = FRONTMATTER_RE.match(text)
    if not m:
        return False
    fm_end = m.end()
    admon = build_admonition(chap_num, chap_dir, chap_title)
    # frontmatter 直後 + 空行を挟む
    rest = text[fm_end:]
    # 既存が改行で始まらない場合は補う
    if rest.startswith("\n"):
        new_text = text[:fm_end] + "\n" + admon + rest
    else:
        new_text = text[:fm_end] + "\n" + admon + "\n" + rest
    md.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    lookup = build_lookup()
    added = 0
    skipped = 0
    for (area, slug), (chap_num, chap_dir, chap_title) in sorted(lookup.items()):
        md = DOCS_DIR / area / f"{slug}.md"
        if not md.exists():
            continue
        if args.dry_run:
            text = md.read_text(encoding="utf-8")
            if MARK_START in text:
                skipped += 1
            else:
                added += 1
                print(f"[would add] {md.relative_to(REPO_ROOT)} -> Topics {chap_num}")
            continue
        if process_file(md, chap_num, chap_dir, chap_title):
            added += 1
            print(f"added: {md.relative_to(REPO_ROOT)} -> Topics {chap_num}")
        else:
            skipped += 1
    print(f"\n合計: 追加 {added} 件 / スキップ {skipped} 件 / 候補総数 {len(lookup)} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
