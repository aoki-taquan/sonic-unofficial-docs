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
# - 旧来の `## 実装との乖離`
# - inject_diff_admonition.py で導入された `!!! diff "HLD と実装の差分"` admonition
DISC_HEADING_RE = re.compile(
    r"^(?:##\s+(?:実装との乖離|現行実装との乖離|HLD と実装の乖離)(?:[^\n]*)"
    r"|!!! diff(?:\s+\"[^\"]*\")?)$",
    re.MULTILINE,
)
# 次の `##` セクション開始 / admonition 終端マーカー
NEXT_HEADING_RE = re.compile(r"^(?:##\s+|<!-- /diff-admonition -->)", re.MULTILINE)

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


_GLOSSARY_LINK_RE = re.compile(
    r"\((?:\.\./)*(?:\./)?reference/glossary\.md(#term-[A-Za-z0-9._-]+)?\)"
)


def _rewrite_glossary_links_for_depth2(text: str) -> str:
    """Rewrite ``(./|../|../../)reference/glossary.md#...`` to the depth-2
    form used by ``docs/reference/verification/discrepancy-index.md``."""
    return _GLOSSARY_LINK_RE.sub(lambda m: f"(../../reference/glossary.md{m.group(1) or ''})", text)


# Match relative markdown links to bare filenames like `(foo-bar.md)` or
# `(foo-bar.md#anchor)` — i.e., same-directory references on the source page.
# Needs to skip glossary (handled separately) and links starting with `../` or
# absolute schemes.
_SAME_DIR_LINK_RE = re.compile(
    r"\(([A-Za-z0-9][A-Za-z0-9._-]*\.md)(#[^)]+)?\)"
)


def _rewrite_same_dir_links_for_depth2(text: str, src_dir: str) -> str:
    """Rewrite same-directory ``(foo.md)`` references on a source page
    (located at ``docs/<src_dir>/<...>.md``) into ``(../../<src_dir>/foo.md)``
    so the summary excerpt embedded in
    ``docs/reference/verification/discrepancy-index.md`` resolves correctly."""
    if not src_dir:
        return text
    return _SAME_DIR_LINK_RE.sub(
        lambda m: f"(../../{src_dir}/{m.group(1)}{m.group(2) or ''})", text
    )


def extract_disc_summary(body: str, src_dir: str = "") -> str:
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

    # `!!! diff` admonition の body は 4 スペース indent されているので剥がす
    if m.group(0).startswith("!!! diff"):
        section = "\n".join(
            line[4:] if line.startswith("    ") else line
            for line in section.split("\n")
        )

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
        # 相対 link のうち glossary 参照は本ページ (depth 2) からの形に書き換える
        text = _rewrite_glossary_links_for_depth2(text)
        # 同一ディレクトリの相対 link（split-child などへの sibling 参照）を
        # discrepancy-index 側で解決可能な形に書き換える
        text = _rewrite_same_dir_links_for_depth2(text, src_dir)
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
        # source page's directory (relative to docs/), e.g. "architecture"
        src_dir = "/".join(parts[:-1]) if len(parts) > 1 else ""
        entries.append(
            {
                "title": fm.get("title", str(rel)),
                "area": fm.get("area", area),
                "last_verified": fm.get("last_verified", ""),
                "monitor": fm.get("monitor", ""),
                "summary": extract_disc_summary(body, src_dir),
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

    # フッター: 品質監査軸 6 の読み替えに関する注記（固定文）
    out.append("## 監査基準の取り扱い")
    out.append("")
    out.append(
        "本ページ群（`verification: discrepancy-found` のページ）は、"
        "「機能としては完結していなくても、代わりに HLD と実装の差分を整理して"
        "読み手に渡す」ことを目的としています。"
        "品質監査 (`meta/quality-audit-*.md`) における **軸 6 (完結性)** は、"
        "本ページ群では「乖離説明の整理度」"
        "（monitor タグ妥当性 / 「実装との乖離」セクションの構造化 / "
        "裏取り evidence / 読み手への next-action）に読み替えて評価します。"
        "詳細は `meta/templates/SCHEMA.md` の "
        "「`discrepancy-found` ページの軸 6 評価基準」セクション、"
        "および `meta/quality-audit-guide.md` を参照してください。"
    )
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
