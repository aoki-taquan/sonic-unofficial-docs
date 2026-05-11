#!/usr/bin/env python3
"""Inject a `<!-- next-action -->` block into `verification: discrepancy-found` pages.

For each discrepancy-found page (≈50 件), insert a templated "次アクション"
section before `## 関連 Topics` (or before the topics-back-ref marker, or
before the glossary-links-injected marker, or at end of file if none of those
exist). Idempotent: if a `<!-- next-action -->` block already exists, the
block is replaced in place.

Usage:
    .venv/bin/python3 meta/scripts/inject_next_action.py            # write
    .venv/bin/python3 meta/scripts/inject_next_action.py --check    # verify

Exit code 0 = success / already in sync. Non-zero = something to write
(when --check is passed) or hard error.

Motivation: audit round 20 found `next-action` 明示率 9% on
`discrepancy-found` pages was the main driver for low 軸 6 評価. This script
lifts the floor by stamping every discrepancy-found page with a minimum
actionable next-step block, hydrated from frontmatter (monitor /
last_verified / related.config_db / related.cli / related.yang).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"PyYAML required: {exc}", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

BEGIN = "<!-- next-action -->"
END = "<!-- /next-action -->"

# monitor 別の actionable advice テンプレ
MONITOR_ADVICE = {
    "not_implemented": (
        "実装が無いため、本機能に依存した運用は不可。"
        "代替機能 (下記リンク) で要件を満たせるか検討する"
    ),
    "partially_implemented": (
        "取り込み済の部分のみ運用可能。"
        "欠落部分の利用は不可なので本文「実装との乖離」を確認した上で適用範囲を限定する"
    ),
    "evolved_beyond_hld": (
        "実装は存在するが本 HLD の記述と乖離。"
        "最新 master の動作を別途確認した上で適用する"
    ),
    "deprecated": (
        "本 HLD は採用見送り。後継機能 (下記リンク) を参照"
    ),
}

# monitor 別の再裏取り cadence
MONITOR_CADENCE = {
    "not_implemented": "quarterly",
    "partially_implemented": "quarterly",
    "evolved_beyond_hld": "quarterly",
    "deprecated": "biannual",
}


@dataclass
class PageMeta:
    path: Path
    frontmatter: dict
    frontmatter_text: str  # 原文の YAML テキスト（書き戻し時にそのまま使う）
    body: str

    @property
    def monitor(self) -> str:
        return str(self.frontmatter.get("monitor") or "evolved_beyond_hld")

    @property
    def last_verified(self) -> str:
        v = self.frontmatter.get("last_verified")
        return str(v) if v else "unknown"

    @property
    def related_refs(self) -> list[tuple[str, str]]:
        """Return [(label, relative_link_from_page)] for related references."""
        out: list[tuple[str, str]] = []
        related = self.frontmatter.get("related") or {}
        page_dir = self.path.parent
        ref_dir = DOCS / "reference"

        def rel_link(target: Path) -> str:
            # Compute markdown relative path from page_dir to target.
            try:
                return str(Path(*[".."] * len(page_dir.relative_to(DOCS).parts)) / target.relative_to(DOCS))
            except ValueError:
                return str(target)

        for table in related.get("config_db") or []:
            slug = str(table).lower().replace("_", "-")
            candidate = ref_dir / "config-db" / f"{slug}.md"
            if candidate.exists():
                out.append((f"CONFIG_DB: {table}", rel_link(candidate)))
        for cmd in related.get("cli") or []:
            slug = str(cmd).strip().replace(" ", "-").lower()
            candidate = ref_dir / "cli" / f"{slug}.md"
            if candidate.exists():
                out.append((f"CLI: `{cmd}`", rel_link(candidate)))
        for mod in related.get("yang") or []:
            slug = str(mod).lower()
            candidate = ref_dir / "yang" / f"{slug}.md"
            if candidate.exists():
                out.append((f"YANG: `{mod}`", rel_link(candidate)))
        return out


def load_page(path: Path) -> Optional[PageMeta]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    if fm.get("verification") != "discrepancy-found":
        return None
    return PageMeta(
        path=path,
        frontmatter=fm,
        frontmatter_text=m.group(1),
        body=m.group(2),
    )


def build_block(page: PageMeta) -> str:
    monitor = page.monitor
    advice = MONITOR_ADVICE.get(monitor, MONITOR_ADVICE["evolved_beyond_hld"])
    cadence = MONITOR_CADENCE.get(monitor, "quarterly")

    refs = page.related_refs
    if refs:
        # 最大 4 件まで出して残りは省略
        ref_lines = "\n".join(
            f"        - [{label}]({link})" for label, link in refs[:4]
        )
        alt_block = "\n    - **代替手段 / 関連 reference**:\n" + ref_lines
    else:
        alt_block = (
            "\n    - **代替手段 / 関連 reference**: 本ページの frontmatter `related` が空のため、"
            "[Reference 索引](../reference/index.md) から関連テーブル / CLI / YANG を辿る"
        )

    # last_verified からの再裏取りトリガ計算は単純化（cadence ラベルのみ表示）
    # 各ページから docs/reference/verification/discrepancy-index.md への相対リンク
    page_dir = page.path.parent
    try:
        depth = len(page_dir.relative_to(DOCS).parts)
    except ValueError:
        depth = 1
    disc_index = ("../" * depth) + "reference/verification/discrepancy-index.md"

    block_inner = f"""## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: {advice}
    - **upstream 動向を追う場合**: 関連 issue / PR を [sonic-net/SONiC](https://github.com/sonic-net/SONiC) で検索（HLD タイトル / CONFIG_DB テーブル名 / Orch クラス名で grep するのが速い）{alt_block}

!!! note "本ドキュメントの追跡"
    - monitor: `{monitor}` / last_verified: `{page.last_verified}`
    - 次回再裏取りトリガ: {cadence}。一覧は [discrepancy-index]({disc_index}) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）
"""

    return f"{BEGIN}\n{block_inner}\n{END}"


# 挿入位置の判定パターン
HEADER_TOPICS_RE = re.compile(r"^## 関連 Topics\s*$", re.MULTILINE)
TOPICS_BACKREF_OPEN_RE = re.compile(r"^<!-- topics-back-ref -->\s*$", re.MULTILINE)
GLOSSARY_INJECTED_RE = re.compile(r"^<!-- glossary-links-injected:[^>]*-->\s*$", re.MULTILINE)
EXISTING_BLOCK_RE = re.compile(
    re.escape(BEGIN) + r".*?" + re.escape(END),
    re.DOTALL,
)


def inject(body: str, block: str) -> str:
    # If a next-action block already exists, replace it in-place (idempotent).
    if EXISTING_BLOCK_RE.search(body):
        return EXISTING_BLOCK_RE.sub(lambda _m: block, body, count=1)

    # Pick the earliest of these anchors and insert before it.
    anchors: list[int] = []
    for pat in (TOPICS_BACKREF_OPEN_RE, HEADER_TOPICS_RE, GLOSSARY_INJECTED_RE):
        m = pat.search(body)
        if m:
            anchors.append(m.start())
    if anchors:
        idx = min(anchors)
        before = body[:idx].rstrip() + "\n\n"
        after = body[idx:]
        return before + block + "\n\n" + after

    # Else append at end of file.
    stripped = body.rstrip()
    return stripped + "\n\n" + block + "\n"


def rebuild_file(page: PageMeta, new_body: str) -> str:
    # 原文の YAML テキストをそのまま再利用し、改行/クォート/順序を保つ
    return f"---\n{page.frontmatter_text}\n---\n{new_body}"


def process(check: bool) -> int:
    changed = 0
    touched = 0
    for md in sorted(DOCS.rglob("*.md")):
        page = load_page(md)
        if page is None:
            continue
        touched += 1
        block = build_block(page)
        new_body = inject(page.body, block)
        if new_body == page.body:
            continue
        changed += 1
        if check:
            print(f"would-update: {md.relative_to(ROOT)}")
        else:
            md.write_text(rebuild_file(page, new_body), encoding="utf-8")
            print(f"updated: {md.relative_to(ROOT)}")

    if check:
        print(f"\n[check] discrepancy-found pages scanned: {touched}, drift: {changed}")
        return 1 if changed else 0
    print(f"\n[write] discrepancy-found pages scanned: {touched}, updated: {changed}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument("--check", action="store_true", help="dry-run; exit non-zero if drift")
    args = ap.parse_args()
    return process(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
