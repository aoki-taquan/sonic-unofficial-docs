#!/usr/bin/env python3
"""Lint: ``monitor: evolved_beyond_hld`` ページの 6C 補完を確認する。

``evolved_beyond_hld`` は「実装は存在するが HLD と形が違う」という monitor
値。実装と HLD のズレが他のページよりも「読み手の混乱要因」になるため、
最低限以下の 2 つが揃っているか lint する:

  (A) HLD と実装の差分が明示されている:
      - ``## 制限事項`` セクションが存在する OR
      - ``!!! diff`` admonition (mkdocs custom) が本文に出現する

  (B) ``## 確認コマンド`` または ``## トラブルシュート`` セクションがあり、
      その配下に **実 master 動作確認用** のコマンドが含まれる:
      - セクション本文が 3 行以上
      - セクション本文に 1 つ以上の fenced code block (```) がある

CI 上は ``--check`` で informational (exit 0) 運用。

Usage:
    python3 meta/scripts/check_evolved_6c.py            # 一覧表示
    python3 meta/scripts/check_evolved_6c.py --check    # informational (exit 0)
    python3 meta/scripts/check_evolved_6c.py --report   # markdown table
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
MONITOR_RE = re.compile(r"^monitor:\s*evolved_beyond_hld\s*$", re.MULTILINE)

LIMITATIONS_H2_RE = re.compile(
    r"^##\s+.*?(制限事項|Limitations|既知の制限|HLD\s*と.*差分|実装との乖離)",
    re.MULTILINE | re.IGNORECASE,
)
DIFF_ADMONITION_RE = re.compile(r"^!!!\s+diff\b", re.MULTILINE)

# 確認コマンド / トラブルシュート の H2
COMMAND_H2_RE = re.compile(
    r"^##\s+(?:[0-9]+\.\s*)?(?:確認コマンド|トラブルシュート(?:ィング|ing)?|"
    r"Verification\s+Commands?|Troubleshoot(?:ing)?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
NEXT_H2_RE = re.compile(r"^##\s+\S", re.MULTILINE)
FENCED_CODE_RE = re.compile(r"^```", re.MULTILINE)


def parse_frontmatter(text: str) -> tuple[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def has_diff_marker(body: str) -> bool:
    if LIMITATIONS_H2_RE.search(body):
        return True
    if DIFF_ADMONITION_RE.search(body):
        return True
    return False


def find_command_section_body(body: str) -> str | None:
    """確認コマンド / トラブルシュート の H2 配下を返す。複数あれば連結。"""
    sections: list[str] = []
    for m in COMMAND_H2_RE.finditer(body):
        start = m.end()
        # 次の H2 を探す
        next_h2 = NEXT_H2_RE.search(body, pos=start)
        end = next_h2.start() if next_h2 else len(body)
        sections.append(body[start:end])
    if not sections:
        return None
    return "\n".join(sections)


def has_verification_commands(body: str) -> bool:
    section = find_command_section_body(body)
    if section is None:
        return False
    # 内容のある行 (空白以外) を 3 行以上要求
    content_lines = [ln for ln in section.splitlines() if ln.strip()]
    if len(content_lines) < 3:
        return False
    # fenced code block が最低 1 つ (``` が 2 回以上 = open/close)
    fences = FENCED_CODE_RE.findall(section)
    if len(fences) < 2:
        return False
    return True


def collect() -> list[dict[str, object]]:
    suspects: list[dict[str, object]] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if not fm:
            continue
        if not MONITOR_RE.search(fm):
            continue
        reasons: list[str] = []
        if not has_diff_marker(body):
            reasons.append("missing '## 制限事項' or '!!! diff'")
        if not has_verification_commands(body):
            reasons.append(
                "missing '## 確認コマンド'/'## トラブルシュート' with 3+ lines and 1 code block"
            )
        if reasons:
            suspects.append(
                {
                    "path": str(md.relative_to(REPO_ROOT)),
                    "reasons": reasons,
                }
            )
    return suspects


def render_report(suspects: list[dict[str, object]]) -> str:
    if not suspects:
        return "No evolved_beyond_hld 6C suspects.\n"
    lines = [
        "# evolved_beyond_hld 6C lint report\n",
        f"Total suspects: {len(suspects)}\n",
        "| Path | reasons |",
        "|---|---|",
    ]
    for s in suspects:
        reasons = "; ".join(s["reasons"])  # type: ignore[arg-type]
        lines.append(f"| `{s['path']}` | {reasons} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="informational (count to stderr, exit 0)")
    ap.add_argument("--report", action="store_true",
                    help="print markdown report to stdout")
    args = ap.parse_args()

    suspects = collect()

    if args.report:
        print(render_report(suspects))
        return 0

    if args.check:
        print(f"evolved_beyond_hld 6C suspects: {len(suspects)}", file=sys.stderr)
        for s in suspects[:30]:
            reasons = "; ".join(s["reasons"])  # type: ignore[arg-type]
            print(f"  {s['path']} -- {reasons}", file=sys.stderr)
        if len(suspects) > 30:
            print(f"  ... and {len(suspects) - 30} more", file=sys.stderr)
        return 0  # informational

    print(f"evolved_beyond_hld 6C suspects: {len(suspects)}")
    for s in suspects:
        reasons = "; ".join(s["reasons"])  # type: ignore[arg-type]
        print(f"  {s['path']} -- {reasons}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
