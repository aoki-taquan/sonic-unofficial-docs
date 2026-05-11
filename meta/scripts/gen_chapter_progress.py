#!/usr/bin/env python3
"""Generate '章構成と進捗' table for 22 topic chapter-index pages.

For each docs/topics/NN-slug/index.md the script inspects the five canonical
sub-pages (concept / setup / operations / internals / advanced) and emits a
progress table surrounded by:

    <!-- chapter-progress -->
    ## 章構成と進捗
    ...table...
    <!-- /chapter-progress -->

Status thresholds:
  - missing file                 -> ❌ 未着手
  - body line count < 100        -> ⚠️ プレースホルダ (NN 行)
  - otherwise                    -> ✅ 完成 (NN 行)

"body line count" excludes the YAML frontmatter so freshly generated stubs
report a realistic value.

The block is inserted (or replaced) just before the `<!-- next-reads -->`
marker if present, else appended at the end of the file body.

`--check` returns exit code 1 when any chapter would change (drift mode for
CI).
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

# Canonical sub-pages tracked by this generator. Order is significant.
SUBPAGES = [
    ("concept.md", "concept"),
    ("setup.md", "setup"),
    ("operations.md", "operations"),
    ("internals.md", "internals"),
    ("advanced.md", "advanced"),
]

# Threshold below which a present sub-page is considered a placeholder.
PLACEHOLDER_LINE_THRESHOLD = 100


def split_frontmatter(text: str):
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
    # count non-empty significance: simple line count of body
    return body.count("\n")


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
        return f"⚠️ プレースホルダ ({info['lines']} 行)"
    return f"✅ 完成 ({info['lines']} 行)"


def verification_cell(info: dict) -> str:
    if not info["present"]:
        return "-"
    return str(info["verification"] or "-")


def build_block(chapter_dir: Path) -> tuple[str, dict]:
    rows = []
    summary = {"missing": 0, "placeholder": 0, "complete": 0}
    for fname, label in SUBPAGES:
        info = inspect_subpage(chapter_dir / fname)
        if not info["present"]:
            summary["missing"] += 1
        elif info["lines"] < PLACEHOLDER_LINE_THRESHOLD:
            summary["placeholder"] += 1
        else:
            summary["complete"] += 1
        rows.append((label, status_cell(info), verification_cell(info)))

    lines = [
        BEGIN,
        "## 章構成と進捗",
        "",
        "| ページ | 状態 | verification |",
        "|---|---|---|",
    ]
    for label, status, verif in rows:
        lines.append(f"| {label} | {status} | {verif} |")
    lines.append("")
    lines.append(END)
    return "\n".join(lines).rstrip() + "\n", summary


def upsert_block(body: str, block: str) -> str:
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)
    body_clean = pattern.sub("", body)

    if NEXT_READS_ANCHOR in body_clean:
        insert_at = body_clean.index(NEXT_READS_ANCHOR)
        before = body_clean[:insert_at].rstrip() + "\n\n"
        after = body_clean[insert_at:]
        return before + block + "\n" + after
    return body_clean.rstrip() + "\n\n" + block


def process_chapter(idx: Path, check_only: bool) -> tuple[bool, dict]:
    slug = idx.parent.name
    text = idx.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        return False, {"slug": slug, "error": "no-frontmatter"}

    block, summary = build_block(idx.parent)
    new_body = upsert_block(body, block)
    if new_body == body:
        return False, {"slug": slug, "changed": False, **summary}

    if check_only:
        return True, {"slug": slug, "changed": True, **summary}

    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=4096)
    idx.write_text("---\n" + fm_text + "---\n" + new_body, encoding="utf-8")
    return True, {"slug": slug, "changed": True, **summary}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any chapter would change (drift mode)",
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
        changed, info = process_chapter(idx, args.check)
        total += 1
        if changed:
            drift += 1
        miss = info.get("missing", 0)
        ph = info.get("placeholder", 0)
        ok = info.get("complete", 0)
        incomplete_total += miss + ph
        tag = "DRIFT" if changed and args.check else ("WROTE" if changed else "OK   ")
        print(
            f"{tag} {info.get('slug')}: complete={ok} placeholder={ph} missing={miss}"
        )
    print(f"---\nProcessed {total} chapters, {drift} changed, "
          f"{incomplete_total} incomplete sub-pages")
    if args.check and drift:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
