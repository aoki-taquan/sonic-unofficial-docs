#!/usr/bin/env python3
"""Mermaid block の典型構文エラーを自動修正する。

対象パターン:

1. flowchart の `node[label]` の label 内に `(` `)` `|` `/` `<` `>` `&` 等の
   メタ文字が裸で出現する場合、label 全体を `"..."` で囲う
2. cylinder shape `node[(label)]` の label 内に `|` `/` 等が含まれる場合、
   `node[("label")]` に置換
3. subgraph title に `(` `)` が含まれる場合: `subgraph ID["title (x)"]`
4. `[/label/]` `[\\label\\]` の trapezoid 形は維持しつつ内部に括弧があれば quote
5. `(label)` round shape の括弧入りも保守的に quote

False positive を避けるため、すでに `"` で quote されているものは触らない。

Usage:
    python3 meta/scripts/fix_mermaid_syntax.py [--apply] [--limit N]

--apply : 実際に書き込み (default は diff の summary のみ)
--limit : 修正する block 件数の上限
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

# 「flowchart label が quote されておらず特殊文字を含む」を検出する正規表現
# 形状: [, (, {, [[, ((, [( のうち [ と [( と ((, [[ を対象に
# 内部に " が無く、特殊文字 ( ) | / < > & ! が含まれる場合に quote する

SPECIAL = re.compile(r"[()|/<>&!]")


def fix_flowchart_labels(block_lines: list[str]) -> tuple[list[str], int]:
    """各行の `id[...]` の label を必要なら quote する。"""
    fixed = 0
    out = []
    # detect diagram type
    first = ""
    for ln in block_lines:
        if ln.strip():
            first = ln.strip()
            break
    is_flow = first.startswith("flowchart") or first.startswith("graph")
    if not is_flow:
        return block_lines, 0

    for line in block_lines:
        new = line
        new, n = _fix_line(new)
        fixed += n
        out.append(new)
    return out, fixed


# label を含む shape: ID[...] ID(...) ID{...} ID[(...)] ID((...)) ID[[...]] ID[/.../] ID[\...\]
# 一旦 ID + opener + body + closer を捕まえる。ネスト無し前提で greedy 制御。

SHAPE_OPENERS = [
    ("[(", ")]"),  # cylinder
    ("((", "))"),  # circle
    ("[[", "]]"),  # subroutine
    ("[/", "/]"),  # trapezoid
    ("[\\", "\\]"),  # alt trapezoid
    ("{{", "}}"),  # hexagon
    ("[", "]"),  # rect
    ("(", ")"),  # round
    ("{", "}"),  # rhombus
]


def _fix_line(line: str) -> tuple[str, int]:
    """line 内の各 shape body を必要に応じて quote。"""
    fixed = 0
    i = 0
    out = []
    n = len(line)
    while i < n:
        # ID prefix (英数字 + _)
        m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", line[i:])
        if not m:
            out.append(line[i])
            i += 1
            continue
        ident = m.group(0)
        j = i + len(ident)
        matched = None
        for opener, closer in SHAPE_OPENERS:
            if line.startswith(opener, j):
                # find closer
                k = line.find(closer, j + len(opener))
                if k >= 0:
                    body = line[j + len(opener) : k]
                    matched = (opener, closer, body, k + len(closer))
                    break
        if not matched:
            out.append(line[i])
            i += 1
            continue
        opener, closer, body, end = matched
        # already quoted?
        stripped = body.strip()
        if stripped.startswith('"') and stripped.endswith('"'):
            out.append(line[i:end])
            i = end
            continue
        if SPECIAL.search(body):
            # quote it
            quoted = '"' + body.replace('"', '\\"') + '"'
            out.append(ident + opener + quoted + closer)
            fixed += 1
            i = end
            continue
        out.append(line[i:end])
        i = end

    return "".join(out), fixed


SUBGRAPH_RE = re.compile(r"^(\s*subgraph\s+)([^\[\"\n]+?)\s*$")

# edge label `|...|` で特殊文字を含むもの (既に " で quote 済みは除外)
EDGE_LABEL_RE = re.compile(r"(--[->]|==[=>]|-\.[\.\-]?->|\.->)\|([^\"|\n]*?)\|")


def fix_edge_labels(block_lines: list[str]) -> tuple[list[str], int]:
    fixed = 0
    out = []
    first = ""
    for ln in block_lines:
        if ln.strip():
            first = ln.strip()
            break
    if not (first.startswith("flowchart") or first.startswith("graph")):
        return block_lines, 0
    for line in block_lines:
        def repl(m: re.Match) -> str:
            nonlocal fixed
            arrow, label = m.group(1), m.group(2)
            if SPECIAL.search(label):
                fixed += 1
                return f'{arrow}|"{label}"|'
            return m.group(0)
        new = EDGE_LABEL_RE.sub(repl, line)
        out.append(new)
    return out, fixed


# subgraph に shape 構文を書いてしまった場合: `subgraph CFG[(CONFIG_DB)]`
# subgraph ID は plain ID のみ可。`subgraph ID["label"]` 形式へ修正する。
SUBGRAPH_SHAPE_RE = re.compile(
    r"^(\s*subgraph\s+)([A-Za-z_][A-Za-z0-9_]*)\[(\(|\[)?([^\]\n]+?)(\)|\])?\]\s*$"
)


def fix_subgraph_shapes(block_lines: list[str]) -> tuple[list[str], int]:
    """`subgraph ID[(label)]` のような shape を `subgraph ID["label"]` に直す。

    既に `subgraph ID["label"]` 形式 (= 内側 opener なし & body が "..." で
    囲まれている) ならスキップする。
    """
    fixed = 0
    out = []
    for line in block_lines:
        m = SUBGRAPH_SHAPE_RE.match(line)
        if not m:
            out.append(line)
            continue
        prefix, sg_id, inner_open, title, inner_close = m.groups()
        title = title.strip()
        # already quoted plain rectangle: skip
        if not inner_open and title.startswith('"') and title.endswith('"'):
            out.append(line)
            continue
        # strip existing surrounding quotes to avoid double-quoting
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1]
        title_q = title.replace('"', '\\"')
        out.append(f'{prefix}{sg_id}["{title_q}"]')
        fixed += 1
    return out, fixed


def fix_subgraph_titles(block_lines: list[str]) -> tuple[list[str], int]:
    """`subgraph Foo (bar)` を `subgraph SG_n["Foo (bar)"]` に書き換える。

    既に `subgraph ID["title"]` 形式のものは触らない。
    特殊文字を含まない bare title はそのまま (mermaid は許容)。
    """
    fixed = 0
    out = []
    counter = 0
    for line in block_lines:
        m = SUBGRAPH_RE.match(line)
        if not m:
            out.append(line)
            continue
        prefix, title = m.group(1), m.group(2).strip()
        if not SPECIAL.search(title):
            out.append(line)
            continue
        counter += 1
        sg_id = f"SG_{counter}"
        out.append(f'{prefix}{sg_id}["{title}"]')
        fixed += 1
    return out, fixed


def process_file(path: Path, apply: bool) -> tuple[int, int]:
    """returns (blocks_fixed, total_replacements)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    i = 0
    blocks_fixed = 0
    total_repl = 0
    while i < len(lines):
        if re.match(r"^\s*```mermaid\s*$", lines[i]):
            start = i
            j = i + 1
            while j < len(lines) and not re.match(r"^\s*```\s*$", lines[j]):
                j += 1
            block = lines[start + 1 : j]
            block, n0 = fix_subgraph_shapes(block)
            block, n1 = fix_subgraph_titles(block)
            block, n2 = fix_flowchart_labels(block)
            block, n3 = fix_edge_labels(block)
            total = n0 + n1 + n2 + n3
            if total > 0:
                blocks_fixed += 1
                total_repl += total
                lines[start + 1 : j] = block
            i = j + 1
            continue
        i += 1
    if apply and blocks_fixed:
        path.write_text("\n".join(lines), encoding="utf-8")
    return blocks_fixed, total_repl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only-paths", type=Path, help="text file: one path per line")
    args = ap.parse_args()

    if args.only_paths:
        paths = [Path(p.strip()) for p in args.only_paths.read_text().splitlines() if p.strip()]
    else:
        paths = sorted(DOCS.rglob("*.md"))

    total_blocks = 0
    total_repl = 0
    files_changed = 0
    for p in paths:
        if not p.exists():
            continue
        b, r = process_file(p, apply=args.apply)
        if b:
            files_changed += 1
            total_blocks += b
            total_repl += r
            print(f"{p.relative_to(ROOT)}: {b} block(s), {r} fix(es)")
        if args.limit and total_blocks >= args.limit:
            break
    print(f"--- files: {files_changed}, blocks: {total_blocks}, replacements: {total_repl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
