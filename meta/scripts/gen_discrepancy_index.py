#!/usr/bin/env python3
"""Generate docs/reference/verification/discrepancy-index.md.

`docs/**/*.md` を走査し、frontmatter の `verification: discrepancy-found`
ページを抽出して area 別に一覧化する。各エントリには:
  - title（ページへのリンク）
  - monitor タグ（`not_implemented` / `evolved_beyond_hld`）
  - 「実装との乖離」セクション最初の段落の要約

冒頭にサマリ（合計件数、area 別件数、monitor タグ別件数）を付ける。
HLD と現行実装の差分を一望できるサイト USP。

Usage:
    .venv/bin/python3 meta/scripts/gen_discrepancy_index.py
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
OUTPUT = DOCS_DIR / "reference" / "verification" / "discrepancy-index.md"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)

# 「実装との乖離」セクションを拾う見出しパターン
DISC_HEADING_RE = re.compile(
    r"^##\s+(?:実装との乖離|現行実装との乖離|HLD と実装の乖離)(?:[^\n]*)$",
    re.MULTILINE,
)
# 次の `##` セクション開始
NEXT_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)

MONITOR_LABEL = {
    "not_implemented": "未実装",
    "evolved_beyond_hld": "HLD と乖離した形で実装/進化",
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
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # ネストや list は最初の行のみ拾う（簡易パーサ）
        if key and value:
            fm[key] = value
    return fm, m.group(2)


def extract_disc_summary(body: str) -> str:
    """「実装との乖離」セクションの最初の段落を返す。

    Markdown の admonition / コードブロックなどは雑に剥がし、最初の段落のみ。
    """
    m = DISC_HEADING_RE.search(body)
    if not m:
        return ""
    start = m.end()
    rest = body[start:]
    nxt = NEXT_HEADING_RE.search(rest)
    section = rest[: nxt.start()] if nxt else rest

    # 最初の段落（空行区切り）を取り出す
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", section) if p.strip()]
    for p in paragraphs:
        # 単なる admonition マーカ / コードブロック / 表 / リスト見出しは skip
        if p.startswith(("```", "|", "!!!", "???")):
            continue
        # 行頭の `- ` を残す通常のリストはそのまま 1 段落として扱う
        # 改行は半角スペースに畳む
        text = re.sub(r"\s+", " ", p).strip()
        # 長すぎる場合は途中で切る
        if len(text) > 400:
            text = text[:400].rstrip() + "…"
        return text
    return ""


def collect() -> list[dict]:
    entries: list[dict] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if fm.get("verification") != "discrepancy-found":
            continue
        rel = md.relative_to(DOCS_DIR)
        parts = rel.parts
        area = parts[0] if len(parts) > 1 else "_root"
        entries.append(
            {
                "title": fm.get("title", str(rel)),
                "area": fm.get("area", area),
                "last_verified": fm.get("last_verified", ""),
                "monitor": fm.get("monitor", ""),
                "summary": extract_disc_summary(body),
                "path": rel.as_posix(),
            }
        )
    return entries


def render(entries: list[dict]) -> str:
    total = len(entries)
    by_area: dict[str, list[dict]] = defaultdict(list)
    by_monitor: dict[str, int] = defaultdict(int)
    for e in entries:
        by_area[e["area"]].append(e)
        by_monitor[e["monitor"] or "(未指定)"] += 1

    out: list[str] = []
    out.append("---")
    out.append("title: HLD と実装の乖離 一覧（discrepancy-index）")
    out.append('description: "HLD と実装の乖離 一覧（discrepancy-index） — このページは、verification: discrepancy-found が付いた全ページを自動収集して並べたものです。meta/scripts/gen_discrepancy_index.py で生成されます。"')
    out.append("verification: meta")
    out.append("last_verified: 2026-05-11")
    out.append("---")
    out.append("")
    out.append("# HLD と実装の乖離 一覧（discrepancy-index）")
    out.append("")
    out.append(
        "このページは、`verification: discrepancy-found` が付いた全ページを"
        "自動収集して並べたものです。`meta/scripts/gen_discrepancy_index.py` で生成されます。"
    )
    out.append("")
    out.append(
        "SONiC コミュニティ master の HLD には、"
        "(1) 設計提案のみで実装が取り込まれなかったもの、"
        "(2) 取り込まれた後に別設計へ置き換えられたもの、"
        "(3) 部分的に取り込まれて HLD の記述と乖離しているもの、"
        "が混在しています。"
        "本プロジェクトでは該当ページに `verification: discrepancy-found` を付け、"
        "frontmatter `monitor:` で次のように分類しています。"
    )
    out.append("")
    out.append("- `not_implemented`: HLD 提案が現行 master に取り込まれていない")
    out.append("- `evolved_beyond_hld`: 取り込まれたが HLD 記述と乖離した形で進化／置換された")
    out.append("")
    out.append(f"全 **{total}** ページ。")
    out.append("")

    # area 別件数
    out.append("## area 別件数")
    out.append("")
    out.append("| area | 件数 |")
    out.append("|------|-----:|")
    for area in sorted(by_area.keys()):
        out.append(f"| `{area}` | {len(by_area[area])} |")
    out.append("")

    # monitor 別件数
    out.append("## monitor タグ別件数")
    out.append("")
    out.append("| monitor | 件数 |")
    out.append("|---------|-----:|")
    for tag in sorted(by_monitor.keys()):
        label = MONITOR_LABEL.get(tag, tag)
        out.append(f"| `{tag}`（{label}） | {by_monitor[tag]} |")
    out.append("")

    # area 別エントリ
    out.append("## エントリ一覧（area 別）")
    out.append("")
    for area in sorted(by_area.keys()):
        out.append(f"### {area}")
        out.append("")
        for e in sorted(by_area[area], key=lambda x: x["title"]):
            # docs/ をルートにした相対 path から、本ファイル (docs/reference/verification/) への相対 link
            # docs/reference/verification/discrepancy-index.md からの相対 = ../../<path>
            link = f"../../{e['path']}"
            tag = e["monitor"] or "(未指定)"
            tag_label = MONITOR_LABEL.get(e["monitor"], "")
            tag_str = f"`{tag}`" + (f"（{tag_label}）" if tag_label else "")
            lv = f" / last_verified: `{e['last_verified']}`" if e["last_verified"] else ""
            out.append(f"- [{e['title']}]({link})  ")
            out.append(f"  monitor: {tag_str}{lv}")
            if e["summary"]:
                out.append(f"  ")
                out.append(f"  {e['summary']}")
            out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="差分があれば exit 1（CI 用、書き込みはしない）",
    )
    args = parser.parse_args()

    entries = collect()
    new_text = render(entries)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if args.check:
        original = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if original != new_text:
            print(
                "ERROR: docs/reference/verification/discrepancy-index.md が古い。"
                "`python3 meta/scripts/gen_discrepancy_index.py` を実行して commit すること。",
                file=sys.stderr,
            )
            import difflib

            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile="discrepancy-index.md (現状)",
                tofile="discrepancy-index.md (期待)",
                n=3,
            )
            sys.stderr.writelines(diff)
            return 1
        print(f"OK: discrepancy-index は最新 ({len(entries)} entries)")
        return 0

    OUTPUT.write_text(new_text, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
