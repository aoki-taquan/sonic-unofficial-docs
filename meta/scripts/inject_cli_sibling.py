#!/usr/bin/env python3
"""Inject "関連 CLI コマンド" sibling cross-link blocks into CLI ref pages.

各 `docs/reference/cli/<slug>.md` のスラグから *verb prefix* (config / show /
clear / debug / sonic / reboot) と *topic 部分* (例: `bgp`, `interface`,
`portchannel`) を切り出し、同じ topic を共有する別 verb のページを 3-5 件
sibling として `## 関連ページ` 直前に挿入する。

挿入ブロックは `<!-- cli-sibling -->` / `<!-- /cli-sibling -->` で囲まれ、
冪等更新ができる。既にブロックがある場合は中身を上書きする。

Usage:
    .venv/bin/python3 meta/scripts/inject_cli_sibling.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = REPO_ROOT / "docs" / "reference" / "cli"

VERBS = ("config", "show", "clear", "debug", "reboot", "sonic")

# topic 部分が短すぎたり一般語のものは sibling 抽出のキーにしない
STOP_TOPICS = {"group", "all", "config", "version", "uptime"}

START_MARK = "<!-- cli-sibling -->"
END_MARK = "<!-- /cli-sibling -->"
# 手動キュレーション宣言。ブロック内にこのマーカーがあれば自動更新しない。
# 自動 token/area マッチで誤った sibling を引き当てるページ
# (例: `show system-health` の topic=system-health が area=platform の
# `config-banner` 等を拾ってしまうケース) で、編集者が siblings を固定したい
# ときに使う。
MANUAL_MARK = "<!-- cli-sibling:manual -->"

TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)


def parse_slug(slug: str) -> tuple[str | None, str]:
    """slug -> (verb, topic). verb が無い場合 verb=None で topic=slug 全体。"""
    for verb in VERBS:
        prefix = verb + "-"
        if slug.startswith(prefix):
            return verb, slug[len(prefix):]
    return None, slug


def topic_tokens(topic: str) -> list[str]:
    """topic を `-` / `_` で割って token のリストにする。

    短いキーで sibling マッチを取りたいので先頭 token を最重視する。
    """
    parts = re.split(r"[-_]", topic)
    return [p for p in parts if p]


def extract_title(text: str, fallback: str) -> str:
    m = TITLE_RE.search(text)
    if m:
        return m.group(1).strip('"')
    return fallback


PageInfo = tuple[str, str, str, set[str]]  # slug, verb, title, tokens


def build_pages(pages: dict[str, Path]) -> list[PageInfo]:
    out: list[PageInfo] = []
    for slug, path in pages.items():
        if slug == "index":
            continue
        verb, topic = parse_slug(slug)
        if verb is None:
            continue
        tokens = set(topic_tokens(topic))
        tokens -= STOP_TOPICS
        if not tokens:
            continue
        title = extract_title(path.read_text(encoding="utf-8"), slug)
        out.append((slug, verb, title, tokens))
    return out


# 大まかな area マップ。token がここに含まれれば「同じ機能領域」と見なし、
# token 直接一致が無くても sibling 候補に挙げる。
AREA_MAP: dict[str, str] = {
    "bgp": "routing", "route": "routing", "ip": "routing", "bfd": "routing",
    "vrf": "routing", "ndp": "routing", "arp": "routing", "default": "routing",
    "vlan": "switching", "mac": "switching", "interface": "switching",
    "portchannel": "switching", "lldp": "switching", "storm": "switching",
    "vxlan": "overlay", "vnet": "overlay", "mclag": "overlay",
    "mirror": "monitoring", "sflow": "monitoring", "snmp": "monitoring",
    "snmpagentaddress": "monitoring", "snmptrap": "monitoring",
    "flowcnt": "monitoring", "techsupport": "monitoring",
    "syslog": "monitoring",
    "acl": "security", "aaa": "security", "ssh": "security",
    "qos": "qos", "buffer": "qos", "pfc": "qos", "pfcwd": "qos",
    "queue": "qos", "priority": "qos", "priority-group": "qos",
    "nat": "nat",
    "platform": "platform", "environment": "platform", "feature": "platform",
    "system": "platform", "kdump": "platform", "reboot": "platform",
    "version": "platform", "uptime": "platform", "clock": "platform",
    "ntp": "platform", "banner": "platform", "services": "platform",
    "mgmt": "mgmt", "mgmt-vrf": "mgmt", "muxcable": "mgmt",
    "dhcp": "mgmt", "warm_restart": "mgmt", "running": "mgmt",
}


def area_of(tokens: set[str]) -> str | None:
    # Deterministic ordering: iterate sorted tokens so repeated runs return
    # the same area for slugs whose tokens map to multiple areas.
    for t in sorted(tokens):
        if t in AREA_MAP:
            return AREA_MAP[t]
    return None


def find_siblings(
    slug: str,
    all_pages: list[PageInfo],
    max_n: int = 5,
) -> list[tuple[str, str, str]]:
    verb, topic = parse_slug(slug)
    if verb is None:
        return []
    tokens = set(topic_tokens(topic)) - STOP_TOPICS
    if not tokens:
        return []
    self_area = area_of(tokens)

    scored: list[tuple[int, str, PageInfo]] = []
    for info in all_pages:
        sl_slug, sl_verb, _sl_title, sl_tokens = info
        if sl_slug == slug:
            continue
        overlap = tokens & sl_tokens
        score = 0
        if overlap:
            # token 直接一致 (強い)
            score += 100 * len(overlap)
            # 別 verb なら更にプラス
            if sl_verb != verb:
                score += 50
        else:
            sl_area = area_of(sl_tokens)
            if self_area and sl_area == self_area:
                # 同 area の弱マッチ
                score += 20
                if sl_verb != verb:
                    score += 10
        if score > 0:
            scored.append((score, sl_slug, info))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [(info[0], info[1], info[2]) for _s, _slug, info in scored[:max_n]]


def render_block(siblings: list[tuple[str, str, str]]) -> str:
    lines = [START_MARK, "### 関連 CLI コマンド", ""]
    for sl_slug, sl_verb, sl_title in siblings:
        cmd = f"{sl_verb} " + " ".join(topic_tokens(parse_slug(sl_slug)[1]))
        lines.append(f"- [`{cmd}`]({sl_slug}.md) — {sl_title}")
    lines.append("")
    lines.append(END_MARK)
    return "\n".join(lines)


BLOCK_RE = re.compile(
    re.escape(START_MARK) + r".*?" + re.escape(END_MARK),
    re.DOTALL,
)
RELATED_HEAD_RE = re.compile(r"^## 関連ページ\s*$", re.MULTILINE)


def insert_block(text: str, block: str) -> str:
    existing = BLOCK_RE.search(text)
    if existing:
        if MANUAL_MARK in existing.group(0):
            # 手動キュレーションされたブロックは触らない
            return text
        return BLOCK_RE.sub(block, text)
    m = RELATED_HEAD_RE.search(text)
    if m:
        # 関連ページ見出しの前に挿入
        return text[: m.start()] + block + "\n\n" + text[m.start() :]
    # 関連ページが無い場合は末尾に追加（glossary-links-injected の前）
    glossary_idx = text.rfind("<!-- glossary-links-injected")
    if glossary_idx != -1:
        return text[:glossary_idx] + block + "\n\n" + text[glossary_idx:]
    return text.rstrip() + "\n\n" + block + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true",
                        help="dry-run; exit 1 if any drift detected")
    parser.add_argument("--min-siblings", type=int, default=3)
    args = parser.parse_args()
    if args.check:
        args.dry_run = True

    pages: dict[str, Path] = {}
    for path in sorted(CLI_DIR.glob("*.md")):
        pages[path.stem] = path

    all_pages = build_pages(pages)

    updated = 0
    skipped = 0
    for slug, path in pages.items():
        if slug == "index":
            continue
        siblings = find_siblings(slug, all_pages)
        if len(siblings) < args.min_siblings:
            skipped += 1
            continue
        block = render_block(siblings)
        text = path.read_text(encoding="utf-8")
        new_text = insert_block(text, block)
        if new_text != text:
            if not args.dry_run:
                path.write_text(new_text, encoding="utf-8")
            updated += 1

    print(f"updated: {updated}, skipped: {skipped}, total: {len(pages)}")
    if args.check and updated > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
