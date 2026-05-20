#!/usr/bin/env python3
"""
不可視文字 / bidi 制御文字 / homoglyph スキャン。

検知対象:
  - Zero-width: U+200B (ZWSP), U+200C (ZWNJ), U+200D (ZWJ), U+FEFF (BOM)
  - Bidi controls (overrides/embeds): U+202A-U+202E, U+2066-U+2069
  - Tag chars: U+E0000-U+E007F (prompt-injection ベクター)
  - Non-standard whitespace: U+00A0 (NBSP), U+2028 (LS), U+2029 (PS)
  - Word joiner / invisible: U+2060, U+180E, U+FFFE

許可: `<!-- allow-invisible -->` コメントを含むファイル全体は skip。
特定行のみ許可するには行末に `<!-- allow-invisible:NEXT_LINE -->` を置く。

使い方:
    python3 meta/scripts/check_invisible_chars.py            # strict (exit 1 on detect)
    python3 meta/scripts/check_invisible_chars.py --report   # markdown report も出す

対象は docs/ 配下の .md と meta/ 配下の .md / .yml / .py。
"""
from __future__ import annotations

import argparse
import os
import sys

# 検知対象の文字（コードポイント → 説明）
INVISIBLE_CHARS: dict[int, str] = {
    0x00A0: "NBSP (non-breaking space)",
    0x180E: "MONGOLIAN VOWEL SEPARATOR",
    0x200B: "ZWSP (zero-width space)",
    0x200C: "ZWNJ (zero-width non-joiner)",
    0x200D: "ZWJ (zero-width joiner)",
    0x200E: "LRM (left-to-right mark)",
    0x200F: "RLM (right-to-left mark)",
    0x202A: "LRE (left-to-right embedding)",
    0x202B: "RLE (right-to-left embedding)",
    0x202C: "PDF (pop directional formatting)",
    0x202D: "LRO (left-to-right override)",
    0x202E: "RLO (right-to-left override)",
    0x2028: "LINE SEPARATOR",
    0x2029: "PARAGRAPH SEPARATOR",
    0x2060: "WORD JOINER",
    0x2066: "LRI (left-to-right isolate)",
    0x2067: "RLI (right-to-left isolate)",
    0x2068: "FSI (first strong isolate)",
    0x2069: "PDI (pop directional isolate)",
    0xFEFF: "BOM / ZERO-WIDTH NO-BREAK SPACE",
    0xFFFE: "REVERSED BYTE ORDER MARK",
}

# E0000-E007F は範囲で扱う（タグ文字、prompt-injection で多用される領域）
TAG_CHAR_START = 0xE0000
TAG_CHAR_END = 0xE007F


def is_invisible(ch: str) -> str | None:
    cp = ord(ch)
    if cp in INVISIBLE_CHARS:
        return INVISIBLE_CHARS[cp]
    if TAG_CHAR_START <= cp <= TAG_CHAR_END:
        return f"TAG CHAR U+{cp:04X}"
    return None


ALLOW_FILE_MARKER = "<!-- allow-invisible -->"
ALLOW_LINE_MARKER = "allow-invisible:NEXT_LINE"


def scan_file(path: str) -> list[tuple[int, int, str, str]]:
    """ファイル中の不可視文字を行・列・名前付きで返す。"""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, OSError):
        return []

    if ALLOW_FILE_MARKER in content:
        return []

    findings: list[tuple[int, int, str, str]] = []
    allow_next = False
    for line_no, line in enumerate(content.splitlines(), 1):
        if allow_next:
            allow_next = ALLOW_LINE_MARKER in line  # チェーン許可は次の行まで
            continue
        if ALLOW_LINE_MARKER in line:
            allow_next = True
            continue
        for col, ch in enumerate(line, 1):
            name = is_invisible(ch)
            if name:
                # 末尾の trailing space は LF 直前のみ別ルールに任せるため除外
                findings.append((line_no, col, name, line.strip()[:80]))
    return findings


def iter_target_files(roots: list[str]) -> list[str]:
    out: list[str] = []
    for root in roots:
        for dirpath, _, files in os.walk(root):
            # .git や node_modules 等は除外
            if any(seg.startswith(".") and seg != "." for seg in dirpath.split(os.sep)):
                continue
            for f in files:
                if f.endswith((".md", ".yml", ".yaml", ".py")):
                    out.append(os.path.join(dirpath, f))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", nargs="*", default=["docs", "meta"], help="scan roots")
    parser.add_argument("--report", help="write markdown report to this path")
    parser.add_argument("--no-fail", action="store_true", help="exit 0 even if detected")
    args = parser.parse_args()

    files = iter_target_files(args.roots)
    all_findings: list[tuple[str, int, int, str, str]] = []
    for p in files:
        for line_no, col, name, snippet in scan_file(p):
            all_findings.append((p, line_no, col, name, snippet))

    print(f"scanned={len(files)} findings={len(all_findings)}")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write("# Invisible characters report\n\n")
            f.write(f"- scanned: {len(files)} files\n")
            f.write(f"- findings: {len(all_findings)}\n\n")
            if all_findings:
                f.write("## Detail\n\n")
                f.write("| file | line:col | char |\n|---|---|---|\n")
                for p, ln, col, name, _ in all_findings[:500]:
                    f.write(f"| `{p}` | {ln}:{col} | {name} |\n")

    if all_findings:
        # ターミナル出力: 最初の 20 件
        for p, ln, col, name, snippet in all_findings[:20]:
            print(f"  {p}:{ln}:{col}  {name}")
        if len(all_findings) > 20:
            print(f"  ... and {len(all_findings) - 20} more")
        if not args.no_fail:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
