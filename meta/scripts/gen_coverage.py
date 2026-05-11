#!/usr/bin/env python3
"""Generate docs/_meta/coverage.md from frontmatter verification status.

`docs/**/*.md` の frontmatter `verification` を集計し、area 別 × verification
状態のマトリクスを Markdown で書き出す。`docs/_meta/coverage.md` を出力。

Usage:
    .venv/bin/python3 meta/scripts/gen_coverage.py
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
OUTPUT = DOCS_DIR / "_meta" / "coverage.md"

# 集計対象の verification 状態（順序固定で表に並べる）
STATES = [
    "code-verified",
    "discrepancy-found",
    "issue-confirmed",
    "hld-only",
    "meta",
    "stub",
]
STATE_LABEL = {
    "code-verified": "code-verified",
    "discrepancy-found": "discrepancy-found",
    "issue-confirmed": "issue-confirmed",
    "hld-only": "hld-only",
    "meta": "meta",
    "stub": "stub",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def collect() -> dict[str, dict[str, int]]:
    """area -> state -> count"""
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = md.relative_to(DOCS_DIR)
        parts = rel.parts
        # トップレベルの index.md などは area なしで "_root" 扱い
        if len(parts) == 1:
            area = "_root"
        else:
            area = parts[0]
        text = md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        state = fm.get("verification", "stub") or "stub"
        # 未知の状態は stub 扱い（テンプレが空のとき）
        if state not in STATES:
            state = "stub"
        matrix[area][state] += 1
    return matrix


def render(matrix: dict[str, dict[str, int]]) -> str:
    lines: list[str] = []
    lines.append("---")
    lines.append("title: カバレッジ")
    lines.append("verification: meta")
    lines.append("last_verified: 2026-05-11")
    lines.append("---")
    lines.append("")
    lines.append("# カバレッジ")
    lines.append("")
    lines.append(
        "このページは `docs/**/*.md` の frontmatter `verification` フィールドを"
        "集計したものです。`meta/scripts/gen_coverage.py` で自動生成されます。"
    )
    lines.append("")
    lines.append(
        "各状態の意味は次のとおりです。"
    )
    lines.append("")
    lines.append("- **code-verified**: HLD と現行 master 実装を突き合わせて整合が取れているページ")
    lines.append("- **discrepancy-found**: 実装と HLD の間に乖離が確認されたページ（[一覧](discrepancies.md)）")
    lines.append("- **issue-confirmed**: GitHub issue / PR で裏取り済みだが実コード突き合わせ未完了のページ")
    lines.append("- **hld-only**: HLD のみを根拠にしたページ（読み手は鵜呑みにせず実コード確認推奨）")
    lines.append("- **meta**: プロジェクト運用のメタページ（このページや discrepancies など）")
    lines.append("- **stub**: 雛形のみ・frontmatter 未設定のページ")
    lines.append("")

    # 全体合計
    totals: dict[str, int] = defaultdict(int)
    for area, counts in matrix.items():
        for state, n in counts.items():
            totals[state] += n
    grand_total = sum(totals.values())

    lines.append("## 全体合計")
    lines.append("")
    lines.append(f"全 **{grand_total}** ページ。")
    lines.append("")
    lines.append("| 状態 | 件数 |")
    lines.append("|------|-----:|")
    for state in STATES:
        lines.append(f"| {STATE_LABEL[state]} | {totals.get(state, 0)} |")
    lines.append("")

    # area 別マトリクス
    lines.append("## area 別マトリクス")
    lines.append("")
    header = "| area | " + " | ".join(STATE_LABEL[s] for s in STATES) + " | 合計 |"
    sep = "|------|" + "|".join(["-----:"] * (len(STATES) + 1)) + "|"
    lines.append(header)
    lines.append(sep)
    for area in sorted(matrix.keys()):
        counts = matrix[area]
        row_total = sum(counts.values())
        cells = [str(counts.get(s, 0)) for s in STATES]
        lines.append(f"| `{area}` | " + " | ".join(cells) + f" | {row_total} |")
    lines.append("")
    lines.append(
        "推移情報（時系列）は本ページでは扱いません。スナップショットのみ。"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="差分があれば exit 1（CI 用、書き込みはしない）",
    )
    args = parser.parse_args()

    matrix = collect()
    new_text = render(matrix)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if args.check:
        original = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if original != new_text:
            print(
                "ERROR: docs/_meta/coverage.md が古い。"
                "`python3 meta/scripts/gen_coverage.py` を実行して commit すること。",
                file=sys.stderr,
            )
            import difflib

            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile="coverage.md (現状)",
                tofile="coverage.md (期待)",
                n=3,
            )
            sys.stderr.writelines(diff)
            return 1
        print("OK: coverage は最新")
        return 0

    OUTPUT.write_text(new_text, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
