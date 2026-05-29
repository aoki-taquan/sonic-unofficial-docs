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
    "partially_implemented": "部分実装",
    "evolved_beyond_hld": "HLD と乖離した形で実装/進化",
    "deprecated": "deprecated（廃止予定 / 撤去済み）",
}

# monitor subtype 別 admonition タイプ（material for mkdocs の組み込みカラー）
# - not_implemented: 危険（赤）  — 設計のみで実装が無い
# - partially_implemented: 注意（黄）— 一部だけ取り込まれている
# - evolved_beyond_hld: 情報（青）— 実装が HLD を超えて進化／置換
# - deprecated: 抽象（グレー）— 廃止予定／撤去
MONITOR_ADMONITION = {
    "not_implemented": "danger",
    "partially_implemented": "warning",
    "evolved_beyond_hld": "info",
    "deprecated": "abstract",
}

# monitor subtype 別の説明文（セクション冒頭で読み手に何を意味するか伝える）
MONITOR_DESCRIPTION = {
    "not_implemented": (
        "HLD は提案 / マージされたが、現行 master のコードには対応する実装が"
        "**全く存在しない**ページ群。HLD を「設計史料」として読む価値はあるが、"
        "「いま動く機能」として参照すると誤読する。"
    ),
    "partially_implemented": (
        "HLD のスコープのうち**一部の構成要素だけ**が現行 master に取り込まれている"
        "ページ群。データ層 / CLI / orch のどれが欠けているかは個別ページで明示。"
    ),
    "evolved_beyond_hld": (
        "HLD で示された設計が、その後**別アーキテクチャに置換された**、または"
        "**HLD の記述を超えて拡張された**ページ群。HLD と現行コードの両方を読まないと"
        "全体像が掴めない。"
    ),
    "deprecated": (
        "実装は存在するが、**廃止予定 / 撤去済み / 後継機能で置き換えられた**ページ群。"
        "互換性のために残っているケースが多い。"
    ),
}

# subtype の並び順（読み手が「最も読み手の誤解を招きやすい」順に並べる）
MONITOR_ORDER = [
    "not_implemented",
    "partially_implemented",
    "evolved_beyond_hld",
    "deprecated",
]


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


def _render_entry_lines(e: dict) -> list[str]:
    """エントリ 1 件を Markdown の箇条書きとして整形。"""
    link = f"../../{e['path']}"
    tag = e["monitor"] or "(未指定)"
    tag_label = MONITOR_LABEL.get(e["monitor"], "")
    tag_str = f"`{tag}`" + (f"（{tag_label}）" if tag_label else "")
    lv = f" / last_verified: `{e['last_verified']}`" if e["last_verified"] else ""
    lines = [
        f"- [{e['title']}]({link})  ",
        f"  area: `{e['area']}` / monitor: {tag_str}{lv}",
    ]
    if e["summary"]:
        lines.append("  ")
        lines.append(f"  {e['summary']}")
    lines.append("")
    return lines


def render(entries: list[dict]) -> str:
    total = len(entries)
    by_area: dict[str, list[dict]] = defaultdict(list)
    by_monitor: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_area[e["area"]].append(e)
        by_monitor[e["monitor"] or "(未指定)"].append(e)

    out: list[str] = []
    out.append("---")
    out.append("title: HLD と実装の乖離 一覧（discrepancy-index）")
    out.append('description: "HLD と実装の乖離 一覧（discrepancy-index） — verification: discrepancy-found が付いた全ページを monitor subtype 別に分類した一覧。meta/scripts/gen_discrepancy_index.py で生成。"')
    out.append("verification: meta")
    out.append("last_verified: 2026-05-13")
    out.append("---")
    out.append("")
    out.append("# HLD と実装の乖離 一覧（discrepancy-index）")
    out.append("")

    # 「このページの使い方」ボックス
    out.append('!!! tip "このページの使い方"')
    out.append("")
    out.append("    SONiC コミュニティ master の HLD は **設計提案リポジトリ** であり、現行コードと一致しているとは限りません。本ページは「HLD だけ読んで誤解しがちな機能」を一望できる USP ページです。読み手は、まず後述の **monitor subtype 別セクション** で該当機能の乖離タイプ（未実装 / 部分実装 / 進化置換 / 廃止）を把握し、そこから個別ページへ降りて `last_verified` と「実装との乖離」セクションの裏取り根拠を確認してください。area 横断で探す場合は末尾の **area 別索引** から辿れます。")
    out.append("")
    out.append(
        f"`verification: discrepancy-found` が付いた全 **{total}** ページを自動収集しています。"
        "本ページは `meta/scripts/gen_discrepancy_index.py` が生成し、CI (`--check`) で常時鮮度を保証します。"
    )
    out.append("")

    # サマリ表 (area 別 / monitor 別)
    out.append("## サマリ")
    out.append("")
    out.append("### monitor subtype 別件数")
    out.append("")
    out.append("| monitor | 件数 | 意味 |")
    out.append("|---------|-----:|------|")
    for tag in MONITOR_ORDER:
        if tag in by_monitor:
            label = MONITOR_LABEL.get(tag, tag)
            out.append(f"| [`{tag}`](#monitor-{tag.replace('_', '-')}) | {len(by_monitor[tag])} | {label} |")
    # 未定義タグ (フォールバック)
    for tag in sorted(by_monitor.keys()):
        if tag not in MONITOR_ORDER:
            label = MONITOR_LABEL.get(tag, tag)
            out.append(f"| `{tag}` | {len(by_monitor[tag])} | {label} |")
    out.append("")

    out.append("### area 別件数")
    out.append("")
    out.append("| area | 件数 |")
    out.append("|------|-----:|")
    for area in sorted(by_area.keys()):
        out.append(f"| [`{area}`](#area-{area}) | {len(by_area[area])} |")
    out.append("")

    # monitor subtype 別セクション (色付き admonition)
    out.append("## monitor subtype 別")
    out.append("")
    out.append(
        "各 subtype を material 組み込みの色付き admonition でラップしています。"
        "色は重要度ではなく **読み手が誤読する危険度** の目安です"
        "（赤=実装ゼロ、黄=一部のみ、青=設計と別物、灰=廃止）。"
    )
    out.append("")

    for tag in MONITOR_ORDER:
        if tag not in by_monitor:
            continue
        admon = MONITOR_ADMONITION.get(tag, "note")
        label = MONITOR_LABEL.get(tag, tag)
        desc = MONITOR_DESCRIPTION.get(tag, "")
        section_entries = by_monitor[tag]
        # subtype 見出し (HTML anchor を明示)
        anchor = f"monitor-{tag.replace('_', '-')}"
        out.append(f"### `{tag}` — {label} ({len(section_entries)} 件) {{#{anchor}}}")
        out.append("")
        out.append(f'!!! {admon} "{label}"')
        out.append("")
        out.append(f"    {desc}")
        out.append("")
        # subtype 内は area → title でソート
        for e in sorted(section_entries, key=lambda x: (x["area"], x["title"])):
            out.extend(_render_entry_lines(e))

    # area 別索引
    out.append("## area 別索引")
    out.append("")
    out.append("area 横断で機能を探したい読み手向けの索引。各エントリは monitor subtype の見出しからもリンクされています。")
    out.append("")
    for area in sorted(by_area.keys()):
        out.append(f"### {area} {{#area-{area}}}")
        out.append("")
        for e in sorted(by_area[area], key=lambda x: x["title"]):
            out.extend(_render_entry_lines(e))

    # この一覧の更新方法
    out.append("## この一覧の更新方法")
    out.append("")
    out.append(
        "本一覧は手で編集しません。エントリの追加・修正は次の経路で行ってください。"
    )
    out.append("")
    out.append("1. **個別ページの修正で十分な場合**：対象ページの frontmatter `verification` / `monitor` / `last_verified` と、本文の「実装との乖離」セクション（または `!!! diff` admonition）を編集して PR を出してください。`gen_discrepancy_index.py` が次の再生成で自動的にエントリを更新します。")
    out.append("2. **新規 discrepancy の報告**：HLD と実装の乖離を新しく見つけた場合は、対象ページに `verification: discrepancy-found` と `monitor: <subtype>` を付け、`.cache/sonic-sources/` を裏取りした根拠を「実装との乖離」セクションに記述してください。`monitor` subtype の選択基準は本ページ上部の表 `monitor subtype 別件数` の「意味」列を参照。")
    out.append("3. **verifier バッチで一括処理する場合**：`meta/prompts/verifier.md` のロール定義に従って verifier サブエージェントを起動し、複数ページの裏取りを並列実行してください。`meta/queue/<area>-<slug>.json` の per-page queue を使うと並走衝突を避けられます。")
    out.append("4. **本一覧 (`discrepancy-index.md`) の再生成**：`.venv/bin/python3 meta/scripts/gen_discrepancy_index.py` で再生成し、生成された差分を commit します。CI では `--check` モードで鮮度が検査されます（差分があると lint 落ちします）。")
    out.append("")
    out.append(
        "issue / 議論は GitHub の Issues に投げてください。"
        "monitor subtype の分類に迷う場合は `meta/templates/SCHEMA.md` を参照してください。"
    )
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
