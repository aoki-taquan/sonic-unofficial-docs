#!/usr/bin/env python3
"""Generate '章構成と進捗' table for docs/topics/*/index.md pages.

For each docs/topics/NN-slug/index.md the script inspects sibling sub-pages
(all .md files except index.md itself) and emits a progress table surrounded
by:

    <!-- chapter-progress -->
    ## 章構成と進捗
    ...table...
    <!-- /chapter-progress -->

Sub-page order is determined by the chapter's .pages YAML file (awesome-pages
format).  If no .pages file exists, pages are listed alphabetically.

Status thresholds:
  - missing file               -> ❌ 未着手
  - body line count < 100      -> ⚠️ プレースホルダ
  - otherwise                  -> ✅ 完成

"body line count" excludes the YAML frontmatter so freshly generated stubs
report a realistic value.

Table columns: ページ | 行数 | 状態 | verification | 主目的

The block is inserted (or replaced) just before the `<!-- next-reads -->`
marker if present, else appended at the end of the file body.

Modes:
  (default)  write mode -- update each index.md in place
  --check    exit code 1 when any chapter would change (drift mode for CI)
  --dry-run  print what would change without writing
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
TOPICS_DIR = DOCS / "topics"

BEGIN = "<!-- chapter-progress -->"
END = "<!-- /chapter-progress -->"
NEXT_READS_ANCHOR = "<!-- next-reads -->"

# Threshold below which a present sub-page is considered a placeholder.
PLACEHOLDER_LINE_THRESHOLD = 100

# Mapping from filename stem to a short Japanese description of purpose.
# Add area-specific pages here as the corpus grows.
PURPOSE_MAP: dict[str, str] = {
    "concept":          "概念・位置付け",
    "architecture":     "アーキテクチャ・データフロー",
    "configuration":    "設定手段の選び方",
    "setup":            "セットアップ手順",
    "operations":       "運用・デバッグ",
    "internals":        "内部実装",
    "advanced":         "発展トピック",
    # area-specific
    "ecmp":             "ECMP 詳細",
    "upgrade":          "アップグレード手順",
    "gnoi-gnsi":        "gNOI / gNSI API",
    "yang-reference":   "YANG リファレンス",
    "cli-index":        "CLI リファレンス索引",
    "config-db-index":  "CONFIG_DB リファレンス索引",
    "yang-index":       "YANG リファレンス索引",
    "quality-gaps":     "品質・カバレッジギャップ",
}


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    try:
        fm = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        fm = None
    return fm, text[end + 5:]


def body_line_count(text: str) -> int:
    _, body = split_frontmatter(text)
    return body.count("\n")


# ---------------------------------------------------------------------------
# Sub-page discovery -- respects .pages order
# ---------------------------------------------------------------------------

def ordered_subpages(chapter_dir: Path) -> list[str]:
    """Return list of sub-page filenames (excluding index.md) in nav order.

    If a .pages file with a ``nav`` key exists, use that order (skipping
    index.md).  Fall back to alphabetical order among .md files.
    """
    pages_file = chapter_dir / ".pages"
    if pages_file.exists():
        try:
            data = yaml.safe_load(pages_file.read_text(encoding="utf-8")) or {}
            nav = data.get("nav", [])
            # nav entries may be plain strings or single-key dicts
            ordered: list[str] = []
            for entry in nav:
                if isinstance(entry, str):
                    fname = entry
                elif isinstance(entry, dict):
                    # e.g. {Title: page.md} -- take the value
                    fname = next(iter(entry.values()), None)
                else:
                    continue
                if fname and fname != "index.md" and fname.endswith(".md"):
                    ordered.append(fname)
            if ordered:
                return ordered
        except yaml.YAMLError:
            pass

    # Fallback: all .md files except index.md, sorted alphabetically
    return sorted(
        p.name
        for p in chapter_dir.glob("*.md")
        if p.name != "index.md"
    )


# ---------------------------------------------------------------------------
# Per-page inspection
# ---------------------------------------------------------------------------

def inspect_subpage(path: Path) -> dict:
    if not path.exists():
        return {"present": False, "lines": 0, "verification": None}
    text = path.read_text(encoding="utf-8")
    fm, _ = split_frontmatter(text)
    lines = body_line_count(text)
    verification = (fm or {}).get("verification")
    return {"present": True, "lines": lines, "verification": verification}


def status_cell(info: dict) -> str:
    if not info["present"]:
        return "❌ 未着手"
    if info["lines"] < PLACEHOLDER_LINE_THRESHOLD:
        return "⚠️ プレースホルダ"
    return "✅ 完成"


def purpose_cell(stem: str) -> str:
    return PURPOSE_MAP.get(stem, "-")


# ---------------------------------------------------------------------------
# Block generation
# ---------------------------------------------------------------------------

def build_block(chapter_dir: Path) -> tuple[str, dict]:
    subpages = ordered_subpages(chapter_dir)
    rows = []
    summary: dict[str, int] = {"missing": 0, "placeholder": 0, "complete": 0}

    for fname in subpages:
        stem = Path(fname).stem
        path = chapter_dir / fname
        info = inspect_subpage(path)

        if not info["present"]:
            summary["missing"] += 1
        elif info["lines"] < PLACEHOLDER_LINE_THRESHOLD:
            summary["placeholder"] += 1
        else:
            summary["complete"] += 1

        line_str = str(info["lines"]) if info["present"] else "-"
        verif = str(info["verification"] or "-") if info["present"] else "-"
        rows.append((
            stem,
            line_str,
            status_cell(info),
            verif,
            purpose_cell(stem),
        ))

    lines_out = [
        BEGIN,
        "## 章構成と進捗",
        "",
        "| ページ | 行数 | 状態 | verification | 主目的 |",
        "|---|---|---|---|---|",
    ]
    for stem, line_str, status, verif, purpose in rows:
        lines_out.append(f"| {stem} | {line_str} | {status} | {verif} | {purpose} |")
    lines_out.append("")
    lines_out.append(END)

    return "\n".join(lines_out).rstrip() + "\n", summary


# ---------------------------------------------------------------------------
# Block upsert into index.md body
# ---------------------------------------------------------------------------

def upsert_block(body: str, block: str) -> str:
    pattern = re.compile(
        re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?",
        re.DOTALL,
    )
    body_clean = pattern.sub("", body)

    if NEXT_READS_ANCHOR in body_clean:
        insert_at = body_clean.index(NEXT_READS_ANCHOR)
        before = body_clean[:insert_at].rstrip() + "\n\n"
        after = body_clean[insert_at:]
        return before + block + "\n" + after
    return body_clean.rstrip() + "\n\n" + block


# ---------------------------------------------------------------------------
# Per-chapter processor
# ---------------------------------------------------------------------------

def process_chapter(
    idx: Path, check_only: bool, dry_run: bool
) -> tuple[bool, dict]:
    slug = idx.parent.name
    text = idx.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        return False, {"slug": slug, "error": "no-frontmatter"}

    block, summary = build_block(idx.parent)
    new_body = upsert_block(body, block)

    # Normalise trailing newline for comparison
    changed = new_body.rstrip("\n") != body.rstrip("\n")
    if not changed:
        return False, {"slug": slug, "changed": False, **summary}

    if check_only or dry_run:
        return True, {"slug": slug, "changed": True, **summary}

    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=4096)
    idx.write_text("---\n" + fm_text + "---\n" + new_body, encoding="utf-8")
    return True, {"slug": slug, "changed": True, **summary}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any chapter would change (drift mode for CI).",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing files.",
    )
    args = ap.parse_args()

    if not TOPICS_DIR.is_dir():
        print(f"topics dir not found: {TOPICS_DIR}", file=sys.stderr)
        return 2

    indexes = sorted(p for p in TOPICS_DIR.glob("*/index.md"))
    drift = 0
    total = 0
    incomplete_total = 0

    for idx in indexes:
        changed, info = process_chapter(idx, args.check, args.dry_run)
        total += 1
        if changed:
            drift += 1
        miss = info.get("missing", 0)
        ph = info.get("placeholder", 0)
        ok = info.get("complete", 0)
        incomplete_total += miss + ph

        if args.check:
            tag = "DRIFT" if changed else "OK   "
        elif args.dry_run:
            tag = "WOULD WRITE" if changed else "OK         "
        else:
            tag = "WROTE" if changed else "OK   "

        print(
            f"{tag} {info.get('slug')}: "
            f"complete={ok} placeholder={ph} missing={miss}"
        )

    print(
        f"---\nProcessed {total} chapters, {drift} changed, "
        f"{incomplete_total} incomplete sub-pages"
    )

    if args.check and drift:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
