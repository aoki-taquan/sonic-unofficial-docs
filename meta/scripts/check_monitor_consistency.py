#!/usr/bin/env python3
"""Lint that checks whether ``monitor:`` frontmatter on
``verification: discrepancy-found`` pages is consistent with the body prose.

Each ``monitor`` value implies a particular kind of discrepancy. If the body
does not contain the keywords typically associated with that flavour, the page
is flagged so a human can re-check whether the tag is right.

``monitor`` taxonomy (current usage):

* ``not_implemented``         — HLD は提案だが master に実装が無い / 対応 PR が
  まだ取り込まれていない。本文に「未実装」「対応 PR 無し」「未取り込み」
  「未対応」等が出現するはず。
* ``partially_implemented``   — 一部だけ実装。本文に「一部のみ」「部分的」等と
  「未実装」 / 「未取り込み」の両方が出現するはず。
* ``evolved_beyond_hld``      — 実装は存在するが HLD と形が違う（名称差・別実装）。
  本文に「名称が異なる」「実装は存在する」「形が違う」「差分」等が出現するはず。
* ``deprecated``              — 採用見送り / 後継への移行。本文に「採用見送り」
  「後継」「migration-to-」等が出現するはず。

Usage:
    python3 meta/scripts/check_monitor_consistency.py            # default report
    python3 meta/scripts/check_monitor_consistency.py --check    # informational (exit 0)
    python3 meta/scripts/check_monitor_consistency.py --report   # markdown table
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FENCED_CODE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# 各 monitor 値ごとに、本文に出現してほしいキーワード群。
# - "any" のリスト → どれか 1 つでも出現すれば OK
# - "all_of_groups" のリスト of リスト → 各グループから 1 つ以上出現すれば OK
MONITOR_RULES: dict[str, dict[str, list]] = {
    "not_implemented": {
        "any": [
            r"未実装",
            r"対応\s*PR\s*(?:無し|なし|未マージ|未取り込み)",
            r"未取り込み",
            r"未対応",
            r"(?:まだ|未だ)実装されていない",
            r"実装は無い",
            r"実装が無い",
            r"master\s*(?:に|では)\s*(?:未|無)",
        ],
    },
    "partially_implemented": {
        "all_of_groups": [
            [r"一部のみ", r"部分的", r"partial", r"一部だけ", r"片方のみ",
             r"部分のみ", r"一部実装", r"部分実装"],
            [r"未実装", r"未取り込み", r"未対応", r"未\s*マージ",
             r"欠落", r"未だ実装", r"実装されていな"],
        ],
    },
    "evolved_beyond_hld": {
        "any": [
            r"名称が異なる",
            r"名前が異なる",
            r"実装は存在",
            r"形が違う",
            r"HLD\s*と\s*差分",
            r"HLD\s*と\s*(?:は|の)\s*差",
            r"差分あり",
            r"別名",
            r"置き換",
            r"renamed",
            r"発展",
            r"進化",
            r"乖離",
        ],
    },
    "deprecated": {
        "any": [
            r"採用見送り",
            r"後継",
            r"migration-to-",
            r"廃止",
            r"deprecat",
            r"移行",
            r"置き換え",
        ],
    },
}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm, text[m.end():]


def strip_noise(body: str) -> str:
    body = HTML_COMMENT_RE.sub("", body)
    body = FENCED_CODE_RE.sub("", body)
    body = INLINE_CODE_RE.sub("", body)
    return body


def check_body(body: str, monitor: str) -> tuple[bool, str]:
    """Return (is_consistent, reason_if_inconsistent)."""
    rule = MONITOR_RULES.get(monitor)
    if rule is None:
        return True, ""  # unknown monitor value → skip
    cleaned = strip_noise(body)

    if "any" in rule:
        for pat in rule["any"]:
            if re.search(pat, cleaned, flags=re.IGNORECASE):
                return True, ""
        return False, f"no keyword from any-group matched for monitor={monitor}"

    if "all_of_groups" in rule:
        missing_groups: list[int] = []
        for idx, group in enumerate(rule["all_of_groups"]):
            matched = any(
                re.search(pat, cleaned, flags=re.IGNORECASE) for pat in group
            )
            if not matched:
                missing_groups.append(idx)
        if missing_groups:
            return False, (
                f"missing keyword(s) from group(s) {missing_groups} "
                f"for monitor={monitor}"
            )
        return True, ""

    return True, ""


def collect() -> list[dict[str, str]]:
    suspects: list[dict[str, str]] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(md.relative_to(REPO_ROOT))
        text = md.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if fm.get("verification") != "discrepancy-found":
            continue
        monitor = fm.get("monitor", "")
        if not monitor:
            continue
        ok, reason = check_body(body, monitor)
        if ok:
            continue
        suspects.append(
            {
                "path": rel,
                "monitor": monitor,
                "reason": reason,
            }
        )
    return suspects


def render_report(suspects: list[dict[str, str]]) -> str:
    if not suspects:
        return "No monitor-consistency suspects found.\n"
    lines = [
        "# monitor consistency report\n",
        f"Total suspects: {len(suspects)}\n",
        "| Path | monitor | reason |",
        "|---|---|---|",
    ]
    for s in suspects:
        lines.append(f"| `{s['path']}` | {s['monitor']} | {s['reason']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="informational mode (count to stderr, exit 0)")
    ap.add_argument("--report", action="store_true",
                    help="print markdown table of suspects to stdout")
    args = ap.parse_args()

    suspects = collect()

    if args.report:
        print(render_report(suspects))
    elif args.check:
        print(f"monitor-consistency suspects: {len(suspects)}", file=sys.stderr)
        for s in suspects[:30]:
            print(f"  {s['path']} [{s['monitor']}] {s['reason']}",
                  file=sys.stderr)
        if len(suspects) > 30:
            print(f"  ... and {len(suspects) - 30} more", file=sys.stderr)
        return 0  # informational — always exit 0
    else:
        print(f"monitor-consistency suspects: {len(suspects)}")
        for s in suspects[:30]:
            print(f"  {s['path']} [{s['monitor']}] {s['reason']}")
        if len(suspects) > 30:
            print(f"  ... and {len(suspects) - 30} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
