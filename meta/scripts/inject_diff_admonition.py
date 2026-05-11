#!/usr/bin/env python3
"""discrepancy-found ページの「実装との乖離」セクションを `!!! diff` admonition で包む。

対象: frontmatter で `verification: discrepancy-found` を持ち、本文中に
`## 実装との乖離` で始まる H2 セクションを含むページ。

変換ルール:
1. H2 見出し行 (`## 実装との乖離` 〜 `## 実装との乖離（裏取りメモ ...）`) を検出
2. 次の H2 (`\n## `) または EOF までを 1 セクションとみなす
3. セクション本文を 4 スペースインデントし、`!!! diff "HLD と実装の差分"` でラップ
4. 元のサブ見出し (`### ...`) はインデント後も Markdown として正しくレンダリングされる
5. `<!-- diff-admonition -->` マーカーで包んで idempotent 化

`--check`: 変換が必要なファイルを列挙して終了コード 1。CI 用。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

MARK_START = "<!-- diff-admonition -->"
MARK_END = "<!-- /diff-admonition -->"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
# `## 実装との乖離` で始まる H2（後ろに括弧書きや空白を許容）
SECTION_HEAD_RE = re.compile(r"^## 実装との乖離[^\n]*$", re.MULTILINE)
NEXT_H2_RE = re.compile(r"^## ", re.MULTILINE)


def is_discrepancy_found(text: str) -> bool:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return False
    fm = m.group(1)
    # `verification: discrepancy-found` を許容（クォート有無、空白問わず）
    return bool(re.search(r"^verification:\s*['\"]?discrepancy-found['\"]?\s*$", fm, re.MULTILINE))


def wrap_section(text: str) -> tuple[str, bool]:
    """セクションを admonition で包んだ結果と、変更が起きたかを返す。"""
    if MARK_START in text:
        return text, False
    m = SECTION_HEAD_RE.search(text)
    if not m:
        return text, False
    head_start = m.start()
    head_end = m.end()
    heading_line = text[head_start:head_end]

    # 次の H2 を探す
    rest_after = text[head_end:]
    nxt = NEXT_H2_RE.search(rest_after)
    if nxt:
        body_end = head_end + nxt.start()
    else:
        body_end = len(text)

    # 本文（heading の改行を除いた後ろ）を抽出
    body = text[head_end:body_end]
    # body の先頭・末尾の余分な改行を整理
    body_stripped = body.strip("\n")

    # 4 スペースインデント（空行はそのまま、非空行のみインデント）
    indented_lines = []
    for line in body_stripped.split("\n"):
        if line.strip() == "":
            indented_lines.append("")
        else:
            indented_lines.append("    " + line)
    indented_body = "\n".join(indented_lines)

    # ラップ後の置換ブロック
    replacement = (
        f"{MARK_START}\n"
        f'!!! diff "HLD と実装の差分"\n'
        f"{indented_body}\n"
        f"{MARK_END}\n"
    )

    # 元の見出し行は `!!! diff "..."` に置き換える（heading は admonition title に集約）
    # 末尾の body の後の改行を 1 行確保
    new_text = text[:head_start] + replacement
    # 次の H2 直前に空行を確保
    if body_end < len(text):
        tail = text[body_end:]
        if not tail.startswith("\n"):
            new_text += "\n" + tail
        else:
            new_text += tail
    return new_text, True


def iter_target_files() -> list[Path]:
    files: list[Path] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        if is_discrepancy_found(text) and SECTION_HEAD_RE.search(text):
            files.append(md)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="変換せず候補のみ表示")
    parser.add_argument("--check", action="store_true",
                        help="変換が必要なファイルがあれば exit 1（CI 用）")
    args = parser.parse_args()

    targets = iter_target_files()
    changed = 0
    skipped = 0
    pending: list[Path] = []

    for md in targets:
        text = md.read_text(encoding="utf-8")
        new_text, did_change = wrap_section(text)
        if not did_change:
            skipped += 1
            continue
        pending.append(md)
        if args.check or args.dry_run:
            print(f"[would wrap] {md.relative_to(REPO_ROOT)}")
            continue
        md.write_text(new_text, encoding="utf-8")
        changed += 1
        print(f"wrapped: {md.relative_to(REPO_ROOT)}")

    print(f"\n合計: 対象 {len(targets)} 件 / 変換 {changed} 件 / スキップ {skipped} 件")
    if args.check and pending:
        print(f"未適用のページが {len(pending)} 件あります。`inject_diff_admonition.py` を実行してください。",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
