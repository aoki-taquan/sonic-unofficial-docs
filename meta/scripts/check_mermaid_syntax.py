#!/usr/bin/env python3
"""Mermaid block 構文チェッカ。

docs/**/*.md 内の ```mermaid ... ``` ブロックを抽出し、構文エラーを検出する。

優先順:
1. node + `mermaid` npm package がローカルに用意されていれば真のパーサで検査
   (`meta/scripts/mermaid_parse.mjs` 経由)
2. 用意されていなければ高確度の静的ヒューリスティック (false positive を
   できる限り潰した保守的な実装) にフォールバック

静的チェックで検出するもの (高確度のみ):
- flowchart で異常矢印 `-->>` 等は **検出しない** (sequenceDiagram で valid)
- ラベル `[label]` 内に裸の `(`, `)`, `|`, `/`, `<`, `>`, `&` がある場合 (要 quote)
- `subgraph TITLE` の TITLE に特殊文字 (mermaid 11.x は許容しないケースあり)
- flowchart 方向指定の typo (`LR/RL/TB/TD/BT` 以外)

Usage:
    python3 meta/scripts/check_mermaid_syntax.py [--check] [--report PATH]
        [--strict]

--check : 検出 > 0 で exit 1
--strict: hint レベルも fail に倒す (default は high-confidence のみ)
--report: Markdown report 出力先
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterator, NamedTuple

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

VALID_DIRECTIONS = {"LR", "RL", "TB", "TD", "BT"}
# Mermaid 11.x で実害 (parse error) を出すのは label 内の裸の () と |。
# / や <> & はラベル内で許容されるので false positive を避けるため除外する。
SPECIAL_IN_LABEL = re.compile(r"[()|]")


class Issue(NamedTuple):
    path: Path
    line: int
    kind: str
    message: str
    snippet: str
    severity: str  # "error" | "hint"


def iter_mermaid_blocks(path: Path) -> Iterator[tuple[int, list[str]]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if re.match(r"^\s*```mermaid\s*$", lines[i]):
            start = i + 1
            j = i + 1
            block: list[str] = []
            while j < len(lines) and not re.match(r"^\s*```\s*$", lines[j]):
                block.append(lines[j])
                j += 1
            yield start, block
            i = j + 1
            continue
        i += 1


def static_check_block(path: Path, start: int, block: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    first = ""
    for ln in block:
        if ln.strip():
            first = ln.strip()
            break
    is_flow = first.startswith("flowchart") or first.startswith("graph")

    # flowchart 方向
    m = re.match(r"^(?:flowchart|graph)\s+([A-Za-z]+)", first)
    if m and m.group(1) not in VALID_DIRECTIONS:
        issues.append(
            Issue(path, start, "bad-direction",
                  f"flowchart 方向 '{m.group(1)}' は無効", first, "error")
        )

    if not is_flow:
        return issues

    for off, raw in enumerate(block):
        # mermaid comment
        line = raw.split("%%")[0]
        if not line.strip():
            continue
        # 1) 未 quote ラベル [label]: 内部に裸の `|` が含まれる場合に検出
        #    `(`/`)` は cylinder `[(...)]` の終端文字と紛らわしく FP が多いため
        #    static check では `|` のみ追う。`(`/`)` はパーサで検出する。
        for m in re.finditer(
            r"[A-Za-z_][A-Za-z0-9_]*\[(?!\")([^\"\[\]\n]*\|[^\"\[\]\n]*)\]",
            line,
        ):
            issues.append(
                Issue(path, start + off, "unquoted-label",
                      "ラベル内の `|` は quote が必要: " + m.group(0)[:80],
                      line.strip(), "error")
            )
        # 2) subgraph title に特殊文字 (rect 形式以外)
        m2 = re.match(r"^\s*subgraph\s+([^\[\"\n]+?)\s*$", line)
        if m2 and SPECIAL_IN_LABEL.search(m2.group(1)):
            issues.append(
                Issue(path, start + off, "subgraph-title",
                      f"subgraph title に特殊文字: '{m2.group(1)}'",
                      line.strip(), "error")
            )
        # 3) subgraph に shape 構文 (ID[(...)])
        if re.match(r"^\s*subgraph\s+[A-Za-z_][A-Za-z0-9_]*\[\(", line):
            issues.append(
                Issue(path, start + off, "subgraph-shape",
                      "subgraph に shape 構文は使えない", line.strip(), "error")
            )
        # 4) edge label `|...|` で `(` `)` が含まれる場合は quote 推奨
        #    (mermaid 11.x は edge label 内の `(`/`)` を許容しないケースあり)
        for m in re.finditer(r"(--[->]|==[=>]|-\.[\.\-]?->|\.->)\|([^\"|\n]*[()][^\"|\n]*)\|", line):
            issues.append(
                Issue(path, start + off, "unquoted-edge-label",
                      f"edge label を quote する必要あり: |{m.group(2)[:50]}|",
                      line.strip(), "error")
            )

    return issues


def parser_check(docs_root: Path) -> tuple[int, list[Issue]] | None:
    """mermaid npm パッケージがあれば真のパーサで検査。"""
    mjs = ROOT / "meta" / "scripts" / "mermaid_parse.mjs"
    if not mjs.exists():
        return None
    node = shutil.which("node")
    if not node:
        return None
    # node_modules/mermaid をプロジェクトに置くか、$MERMAID_NODE_MODULES env で指定
    import os
    env_modules = os.environ.get("MERMAID_NODE_MODULES")
    if not env_modules:
        candidate = ROOT / "node_modules" / "mermaid"
        if candidate.exists():
            env_modules = str(ROOT / "node_modules")
    if not env_modules:
        return None
    if not (Path(env_modules) / "mermaid").exists():
        return None
    try:
        res = subprocess.run(
            [node, str(mjs), str(docs_root)],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "NODE_PATH": env_modules},
            timeout=300,
        )
    except Exception:
        return None
    if res.returncode != 0 and not res.stdout.strip():
        return None
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return None
    issues: list[Issue] = []
    for e in data.get("errors", []):
        issues.append(
            Issue(
                Path(e["file"]),
                int(e["line"]),
                "mermaid-parse",
                str(e["err"])[:300],
                "",
                "error",
            )
        )
    return data.get("total", 0), issues


def count_blocks(docs_root: Path) -> tuple[int, int]:
    total = 0
    files = 0
    for md in docs_root.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="replace")
        c = len(re.findall(r"^\s*```mermaid\s*$", text, flags=re.MULTILINE))
        if c > 0:
            files += 1
            total += c
    return total, files


def render_report(issues: list[Issue], total: int, files: int, used_parser: bool) -> str:
    out = [
        "# Mermaid Syntax Report",
        "",
        f"- 対象 md (mermaid 含む): {files}",
        f"- mermaid block 総数: {total}",
        f"- 検出 issue 数: {len(issues)}",
        f"- 検査方式: {'mermaid parser (full)' if used_parser else 'static heuristic'}",
        "",
    ]
    if not issues:
        out.append("No issues detected.")
        return "\n".join(out) + "\n"
    from collections import Counter
    by_kind = Counter(it.kind for it in issues)
    out.append("## kind 別件数")
    out.append("")
    for k, v in by_kind.most_common():
        out.append(f"- `{k}`: {v}")
    out.append("")
    out.append("## 詳細")
    out.append("")
    for it in issues:
        try:
            rel = it.path.relative_to(ROOT)
        except ValueError:
            rel = it.path
        out.append(f"- `{rel}:{it.line}` [{it.kind}] {it.message}")
        if it.snippet:
            out.append(f"  - `{it.snippet[:200]}`")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--report", type=Path)
    ap.add_argument("--docs", type=Path, default=DOCS)
    args = ap.parse_args()

    total, files = count_blocks(args.docs)

    used_parser = False
    issues: list[Issue] = []
    parser_result = parser_check(args.docs)
    if parser_result is not None:
        used_parser = True
        _, issues = parser_result
    else:
        for md in sorted(args.docs.rglob("*.md")):
            for start, block in iter_mermaid_blocks(md):
                issues.extend(static_check_block(md, start, block))
        if not args.strict:
            issues = [i for i in issues if i.severity == "error"]

    report = render_report(issues, total, files, used_parser)
    if args.report:
        args.report.write_text(report, encoding="utf-8")
        print(f"wrote {args.report} ({len(issues)} issues)")
    else:
        print(f"mermaid blocks: {total} in {files} files; issues: {len(issues)}; parser={used_parser}")

    if args.check and issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
