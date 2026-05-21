#!/usr/bin/env python3
"""Update the quality banner in docs/index.md.

集計対象:
- `docs/**/*.md` を走査して frontmatter `verification` を集計し、
  `code-verified` / `discrepancy-found` / `hld-only` 件数を出す
- `meta/quality-audit-*.md` の最大 round 番号のファイルから「全体平均」を抽出
  - 10 段階 (round 7 以降想定): `全 NN 件 加重平均: X.XX / 10`
  - 5 段階 (round 6 以前): `平均: X.XX / 5.0`（または `**round N 全体平均: X.XX / 5.0**`）

`docs/index.md` の以下マーカー間を生成内容で置換する:

    <!-- quality-banner-start -->
    ...自動生成された admonition...
    <!-- quality-banner-end -->

Usage:
    python3 meta/scripts/gen_index_banner.py              # 書き込み
    python3 meta/scripts/gen_index_banner.py --check      # 差分があれば exit 1
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
INDEX_MD = DOCS_DIR / "index.md"
AUDIT_GLOB = "quality-audit-*.md"
AUDIT_DIR = REPO_ROOT / "meta"

MARK_START = "<!-- quality-banner-start -->"
MARK_END = "<!-- quality-banner-end -->"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
VERIFICATION_RE = re.compile(r"^verification:\s*(\S+)", re.MULTILINE)

AUDIT_NUM_RE = re.compile(r"quality-audit-(\d+)\.md$")
# 10 段階加重平均
AVG_10_RE = re.compile(r"全\s*(\d+)\s*件\s*加重平均[:：]\s*([0-9]+\.[0-9]+)\s*/\s*10")
# 5 段階全体平均（バリエーション複数）
AVG_5_PATTERNS = [
    re.compile(r"round\s*\d+\s*全体平均[:：]\s*([0-9]+\.[0-9]+)\s*/\s*5\.0"),
    re.compile(r"\*\*平均[:：]\s*([0-9]+\.[0-9]+)\s*/\s*5\.0\*\*"),
    re.compile(r"平均[:：]\s*([0-9]+\.[0-9]+)\s*/\s*5\.0"),
    # weighted/stratified テーブル形式: `| **総平均** | **4.986 / 5** | ...`
    re.compile(r"\*\*総平均\*\*\s*\|\s*\*\*([0-9]+\.[0-9]+)\s*/\s*5"),
]

# 保守フェーズ移行フラグ。`meta/maintenance-mode.md` が存在すれば運用中とみなす
MAINTENANCE_FLAG = REPO_ROOT / "meta" / "maintenance-mode.md"


def collect_verification_counts() -> Counter:
    counts: Counter = Counter()
    for md in DOCS_DIR.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="replace")
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue
        vm = VERIFICATION_RE.search(m.group(1))
        if not vm:
            continue
        counts[vm.group(1).strip().strip('"').strip("'")] += 1
    return counts


def latest_audit() -> tuple[int, Path] | None:
    candidates: list[tuple[int, Path]] = []
    for f in AUDIT_DIR.glob(AUDIT_GLOB):
        m = AUDIT_NUM_RE.search(f.name)
        if m:
            candidates.append((int(m.group(1)), f))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1]


def extract_average(audit_path: Path) -> tuple[float, str] | None:
    """returns (value, scale_label) e.g. (9.65, "10") or (4.97, "5.0")."""
    text = audit_path.read_text(encoding="utf-8", errors="replace")
    m = AVG_10_RE.search(text)
    if m:
        return float(m.group(2)), "10"
    for pat in AVG_5_PATTERNS:
        m = pat.search(text)
        if m:
            return float(m.group(1)), "5.0"
    return None


def build_banner() -> str:
    counts = collect_verification_counts()
    cv = counts.get("code-verified", 0)
    rv = counts.get("runbook-verified", 0)
    dn = counts.get("discrepancy-found", 0)
    hld = counts.get("hld-only", 0)

    audit = latest_audit()
    audit_line: str
    if audit is None:
        audit_line = "- **監査平均評価**: （quality-audit レポート未検出）"
    else:
        round_num, path = audit
        avg = extract_average(path)
        if avg is None:
            audit_line = (
                f"- **監査平均評価**: round {round_num} 集計中（`{path.relative_to(REPO_ROOT)}`）"
            )
        else:
            value, scale = avg
            audit_line = (
                f"- **監査平均評価**: {value:.2f} / {scale}"
                f"（quality-audit round {round_num}）"
            )

    hld_line = (
        "- すべての本文ページが `hld-only` を脱却し、`code-verified` または "
        "`discrepancy-found` に到達済み"
        if hld == 0
        else f"- **hld-only ページ**: {hld} 件（裏取り待ち）"
    )

    lines = [
        MARK_START,
        "!!! success \"最新の品質状態\"",
        f"    - **code-verified ページ**: {cv} 件（HLD と実コードを照合済み）",
        f"    - **runbook-verified ページ**: {rv} 件（Runbook 専用。実運用で症状再現性が確認済み）",
        f"    - **discrepancy-found ページ**: {dn} 件（HLD と実装の乖離を明示）",
        f"    {audit_line}",
        f"    {hld_line}",
    ]
    if MAINTENANCE_FLAG.exists():
        lines.append(
            "    - **保守フェーズ運用中** "
            "(2026-05-13〜): 月次 master 追従 / 偶数 round stratified audit / "
            "feedback 反映で 4.97+ プラトーを維持 "
            "(`meta/maintenance-mode.md`)"
        )
    lines.append(MARK_END)
    return "\n".join(lines)


OPT_OUT_MARKER = "<!-- no-quality-banner -->"


def replace_banner(original: str, new_banner: str) -> str:
    if OPT_OUT_MARKER in original:
        # ページ側が明示的に「banner を載せない」と宣言している → no-op
        return original
    if MARK_START not in original or MARK_END not in original:
        # 既存のレガシー admonition（`!!! success "最新の品質状態"` ブロック）を
        # 検出して置換する
        legacy = re.search(
            r"!!! success \"最新の品質状態\"\n(?:    .*\n)+",
            original,
        )
        if legacy:
            return original.replace(legacy.group(0), new_banner + "\n")
        # マーカーも legacy ブロックも無い場合は冒頭の H1 直後に挿入
        return re.sub(
            r"(# .*\n\n[^\n]*\n\n)",
            r"\1" + new_banner + "\n\n",
            original,
            count=1,
        )
    return re.sub(
        re.escape(MARK_START) + r".*?" + re.escape(MARK_END),
        new_banner,
        original,
        count=1,
        flags=re.DOTALL,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="差分があれば exit 1（CI 用、書き込みはしない）",
    )
    args = parser.parse_args()

    if not INDEX_MD.exists():
        print(f"ERROR: {INDEX_MD} が存在しない", file=sys.stderr)
        return 2

    original = INDEX_MD.read_text(encoding="utf-8")
    banner = build_banner()
    updated = replace_banner(original, banner)

    if args.check:
        if original != updated:
            print(
                "ERROR: docs/index.md の品質バナーが古い。"
                "`python3 meta/scripts/gen_index_banner.py` を実行して commit すること。",
                file=sys.stderr,
            )
            # diff っぽいヒント
            import difflib

            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile="docs/index.md (現状)",
                tofile="docs/index.md (期待)",
                n=3,
            )
            sys.stderr.writelines(diff)
            return 1
        print("OK: 品質バナーは最新")
        return 0

    if original == updated:
        print("変更なし: 品質バナーは既に最新")
        return 0
    INDEX_MD.write_text(updated, encoding="utf-8")
    print(f"更新: {INDEX_MD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
