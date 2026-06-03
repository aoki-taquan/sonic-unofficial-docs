#!/usr/bin/env python3
"""verifier の `<!-- evidence: ... -->` HTML コメントを読み手向け collapsible
admonition として本文に現出させる。

HTML コメントは verifier 自動裏取りの根拠として残し、その直後に
``<!-- evidence-rendered:start -->`` ... ``<!-- evidence-rendered:end -->``
で囲んだ ``??? note "📋 検証エビデンス: <source>"`` ブロックを挿入する。

サポートする evidence の書式 (YAML ライク):

    <!-- evidence:
    source: <repo>/<path>#L<a>-L<b> (sha: <sha>)
    excerpt: |
      <multi-line excerpt>
    reasoning: <one-line reasoning>
    -->

``--check`` を渡すと drift（未生成 / 古い内容）があった時に exit 1。
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

EVIDENCE_RE = re.compile(
    r"<!--\s*evidence:\s*\n(?P<body>.*?)-->",
    re.DOTALL,
)
RENDERED_BLOCK_RE = re.compile(
    r"\n<!-- evidence-rendered:start -->\n.*?\n<!-- evidence-rendered:end -->\n",
    re.DOTALL,
)

MARK_START = "<!-- evidence-rendered:start -->"
MARK_END = "<!-- evidence-rendered:end -->"


@dataclass
class Evidence:
    source: str
    excerpt: str
    reasoning: str


def parse_evidence(body: str) -> Evidence | None:
    """YAML ライクな body を厳密にではなく十分に parse する。"""
    source = ""
    excerpt_lines: list[str] = []
    reasoning_lines: list[str] = []
    reasoning = ""

    lines = body.splitlines()
    i = 0

    def consume_block_scalar(start_i: int, base_indent: int, style: str) -> tuple[list[str], int]:
        """`|` (literal) / `>` (folded) ブロックスカラーの継続行を取り込み、
        (取り込んだ行, 次の i) を返す。folded スタイルでは空行は段落区切り、
        通常の継続行は単一スペースで join する。"""
        collected: list[str] = []
        j = start_i
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                collected.append("")
                j += 1
                continue
            indent = len(nxt) - len(nxt.lstrip())
            if indent <= base_indent:
                break
            collected.append(nxt[base_indent + 2:] if len(nxt) > base_indent + 2 else nxt.lstrip())
            j += 1
        if style == ">":
            # folded: 空行は段落区切り、連続行はスペース join
            paragraphs: list[str] = []
            buf: list[str] = []
            for ln in collected:
                if ln == "":
                    if buf:
                        paragraphs.append(" ".join(buf))
                        buf = []
                    paragraphs.append("")
                else:
                    buf.append(ln)
            if buf:
                paragraphs.append(" ".join(buf))
            while paragraphs and paragraphs[-1] == "":
                paragraphs.pop()
            return paragraphs, j
        return collected, j

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("source:"):
            source = stripped[len("source:"):].strip()
            i += 1
        elif stripped.startswith("excerpt:"):
            rest = stripped[len("excerpt:"):].strip()
            if rest == "|" or rest == ">":
                base_indent = len(line) - len(line.lstrip())
                collected, i = consume_block_scalar(i + 1, base_indent, rest)
                excerpt_lines.extend(collected)
            else:
                excerpt_lines.append(rest)
                i += 1
        elif stripped.startswith("reasoning:"):
            rest = stripped[len("reasoning:"):].strip()
            if rest == "|" or rest == ">":
                base_indent = len(line) - len(line.lstrip())
                collected, i = consume_block_scalar(i + 1, base_indent, rest)
                reasoning_lines.extend(collected)
            else:
                reasoning_lines.append(rest)
                i += 1
        else:
            i += 1

    if reasoning_lines:
        # reasoning は `**判断根拠**: <text>` の inline 形式でレンダリングされるため、
        # 改行・段落区切りを半角スペースに畳んで 1 行化する。
        joined = "\n".join(reasoning_lines).strip()
        reasoning = re.sub(r"\s*\n+\s*", " ", joined).strip()

    if not source and not excerpt_lines and not reasoning:
        return None
    excerpt = "\n".join(excerpt_lines).strip("\n")
    return Evidence(source=source, excerpt=excerpt, reasoning=reasoning)


def render_block(ev: Evidence) -> str:
    """??? note collapsible details ブロックを生成する。"""
    # title はダブルクオート安全化
    title_source = ev.source if ev.source else "(source 未指定)"
    title_source = title_source.replace('"', "'")
    lines: list[str] = []
    lines.append(MARK_START)
    lines.append(f'??? note "📋 検証エビデンス: {title_source}"')
    lines.append("")
    lines.append("    **出典**:")
    lines.append("")
    lines.append(f"    `{ev.source}`" if ev.source else "    (出典未指定)")
    lines.append("")
    if ev.excerpt:
        lines.append("    **抜粋**:")
        lines.append("")
        lines.append("    ```text")
        for ex_line in ev.excerpt.splitlines():
            lines.append(f"    {ex_line}" if ex_line else "    ")
        lines.append("    ```")
        lines.append("")
    if ev.reasoning:
        lines.append("    **判断根拠**: " + ev.reasoning)
        lines.append("")
    lines.append(MARK_END)
    return "\n" + "\n".join(lines) + "\n"


def process_file(path: Path) -> tuple[str, int]:
    """ファイルを処理し、(新しい内容, 挿入/更新件数) を返す。"""
    original = path.read_text(encoding="utf-8")
    # まず既存の rendered ブロックを全削除（後で再生成）
    cleaned = RENDERED_BLOCK_RE.sub("\n", original)

    # その後 evidence コメントを再走査して直後に rendered を入れ直す
    out_parts: list[str] = []
    last = 0
    count = 0
    for m in EVIDENCE_RE.finditer(cleaned):
        ev = parse_evidence(m.group("body"))
        # コメントそのものはそのまま残す
        out_parts.append(cleaned[last:m.end()])
        last = m.end()
        if ev is None:
            continue
        # 既に末尾改行が無ければ補う
        if not out_parts[-1].endswith("\n"):
            out_parts.append("\n")
        out_parts.append(render_block(ev))
        count += 1
    out_parts.append(cleaned[last:])
    new_content = "".join(out_parts)
    # 連続改行の最大 2 行への正規化（過剰挿入回避）
    new_content = re.sub(r"\n{3,}", "\n\n", new_content)
    return new_content, count


def iter_target_files() -> Iterable[Path]:
    for path in sorted(DOCS_DIR.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "<!-- evidence:" in text:
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="drift 検知のみ。書き込みしない")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    drift: list[Path] = []
    written = 0
    total_blocks = 0
    pages = 0
    for path in iter_target_files():
        pages += 1
        new_content, count = process_file(path)
        total_blocks += count
        old = path.read_text(encoding="utf-8")
        if new_content != old:
            if args.check:
                drift.append(path)
            else:
                path.write_text(new_content, encoding="utf-8")
                written += 1
                if args.verbose:
                    print(f"updated: {path.relative_to(REPO_ROOT)} ({count} blocks)")
        elif args.verbose:
            print(f"unchanged: {path.relative_to(REPO_ROOT)} ({count} blocks)")

    if args.check:
        if drift:
            print(f"[render_evidence] drift detected in {len(drift)} files:", file=sys.stderr)
            for p in drift:
                print(f"  - {p.relative_to(REPO_ROOT)}", file=sys.stderr)
            print("Run: python meta/scripts/render_evidence.py", file=sys.stderr)
            return 1
        print(f"[render_evidence] OK: {pages} pages scanned, {total_blocks} evidence blocks in sync")
        return 0

    print(f"[render_evidence] {pages} pages scanned, {written} updated, {total_blocks} evidence blocks rendered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
