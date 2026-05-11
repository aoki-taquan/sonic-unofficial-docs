#!/usr/bin/env python3
"""Auto-populate `description:` frontmatter for docs/**/*.md.

For pages that don't yet have a `description:` field, derive one from the page
H1 + the first prose paragraph after the first heading, and insert it into the
frontmatter block. mkdocs-material exposes `description` as the HTML
`<meta name="description">` tag, improving search-engine snippets.

Heuristics:
  - Description is 100-150 characters (Japanese aware: counted as characters,
    not bytes).
  - Skip admonitions (`!!! ...`), HTML comments, code fences, tables, lists.
  - Strip Markdown inline syntax (links, bold, italics, code, footnotes).
  - Use H1 as a fallback / prefix when no prose paragraph is found.
  - Idempotent: re-running the script does nothing if a description is already
    present (and non-empty).

Usage:
  python meta/scripts/gen_descriptions.py            # update all docs
  python meta/scripts/gen_descriptions.py --dry-run  # report only
  python meta/scripts/gen_descriptions.py --check    # exit 1 if any page lacks
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
# Strip frequently-seen Markdown decorations.
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
FOOTNOTE_RE = re.compile(r"\[\^[^\]]+\]")
HTML_TAG_RE = re.compile(r"<[^>]+>")

TARGET_MIN = 100
TARGET_MAX = 150
HARD_MAX = 160  # safety cap for very long single sentences

# Sentence-ish split points for Japanese + English.
SENT_SPLIT_RE = re.compile(r"(?<=[。．！？!?])")


def split_frontmatter(text: str) -> tuple[str | None, str]:
    m = FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def has_description(fm_raw: str) -> bool:
    for line in fm_raw.splitlines():
        if line.startswith("description:"):
            val = line.split(":", 1)[1].strip()
            # treat empty or quoted-empty as missing
            if val and val not in ("''", '""'):
                return True
    return False


def clean_text(s: str) -> str:
    s = IMAGE_RE.sub("", s)
    s = LINK_RE.sub(r"\1", s)
    s = INLINE_CODE_RE.sub(r"\1", s)
    s = BOLD_RE.sub(r"\1", s)
    s = ITALIC_RE.sub(r"\1", s)
    s = FOOTNOTE_RE.sub("", s)
    s = HTML_TAG_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_prose_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith(("#", ">", "|", "-", "*", "+", "!!!", "    ", "```", "~~~", ":::")):
        return False
    if s.startswith(("<!--", "<")):
        return False
    if re.match(r"^\d+\.\s", s):
        return False
    return True


def collect_prose_paragraphs(body: str) -> list[str]:
    """Return prose paragraphs in body order, skipping non-prose blocks."""
    paras: list[str] = []
    cur: list[str] = []
    in_code = False
    in_admonition = False
    admonition_indent = 0

    for raw in body.splitlines():
        line = raw.rstrip()

        # code fence toggle
        if line.startswith("```") or line.startswith("~~~"):
            if cur:
                paras.append(" ".join(cur).strip())
                cur = []
            in_code = not in_code
            continue
        if in_code:
            continue

        # admonition: skip indented continuation lines until dedent
        if in_admonition:
            if line.startswith(" " * admonition_indent) or not line.strip():
                continue
            in_admonition = False

        if line.lstrip().startswith("!!!"):
            in_admonition = True
            admonition_indent = len(line) - len(line.lstrip()) + 4
            if cur:
                paras.append(" ".join(cur).strip())
                cur = []
            continue

        if not line.strip():
            if cur:
                paras.append(" ".join(cur).strip())
                cur = []
            continue

        if not is_prose_line(line):
            if cur:
                paras.append(" ".join(cur).strip())
                cur = []
            continue

        cur.append(line.strip())

    if cur:
        paras.append(" ".join(cur).strip())
    return [p for p in paras if p]


def extract_h1(body: str) -> str | None:
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("# ") and not s.startswith("## "):
            return clean_text(s[2:].strip())
    return None


def trim_to_window(s: str, max_len: int = TARGET_MAX) -> str:
    """Trim `s` to <= max_len characters, preferring sentence boundaries."""
    if len(s) <= max_len:
        return s
    # try to cut at a sentence boundary within budget
    sentences = SENT_SPLIT_RE.split(s)
    out = ""
    for sent in sentences:
        if not sent:
            continue
        if len(out) + len(sent) > max_len:
            if out:
                return out.rstrip()
            # single huge sentence: hard-truncate
            return sent[: max_len - 1].rstrip() + "…"
        out += sent
        if len(out) >= TARGET_MIN:
            return out.rstrip()
    return out.rstrip() or s[: max_len - 1] + "…"


def build_description(h1: str | None, paragraphs: list[str], title: str | None) -> str:
    seed = h1 or title or ""
    # Pick the first informative paragraph (length >= 30 chars to skip stubs).
    body_pick: str | None = None
    for p in paragraphs:
        cleaned = clean_text(p)
        if len(cleaned) >= 30:
            body_pick = cleaned
            break
    if body_pick is None and paragraphs:
        body_pick = clean_text(paragraphs[0])

    if seed and body_pick:
        combined = f"{seed} — {body_pick}"
    elif body_pick:
        combined = body_pick
    elif seed:
        combined = seed
    else:
        return ""

    combined = re.sub(r"\s+", " ", combined).strip()
    return trim_to_window(combined, HARD_MAX)


def yaml_escape(s: str) -> str:
    # Use double-quoted YAML scalar; escape backslashes and double quotes.
    return s.replace("\\", "\\\\").replace('"', '\\"')


def insert_description(fm_raw: str, description: str) -> str:
    """Insert `description:` into frontmatter just after `title:` (or at end)."""
    lines = fm_raw.split("\n")
    out: list[str] = []
    inserted = False
    desc_line = f'description: "{yaml_escape(description)}"'
    for i, line in enumerate(lines):
        out.append(line)
        if not inserted and line.startswith("title:"):
            out.append(desc_line)
            inserted = True
    if not inserted:
        out.append(desc_line)
    return "\n".join(out)


def get_title(fm_raw: str) -> str | None:
    for line in fm_raw.splitlines():
        if line.startswith("title:"):
            val = line.split(":", 1)[1].strip()
            val = val.strip("'\"")
            return val or None
    return None


def process_file(path: Path, *, dry_run: bool) -> tuple[bool, str]:
    """Return (changed, description). changed=False if already present or skipped."""
    text = path.read_text(encoding="utf-8")
    fm_raw, body = split_frontmatter(text)
    if fm_raw is None:
        return False, ""
    if has_description(fm_raw):
        return False, ""
    h1 = extract_h1(body)
    paras = collect_prose_paragraphs(body)
    title = get_title(fm_raw)
    desc = build_description(h1, paras, title)
    if not desc:
        return False, ""
    new_fm = insert_description(fm_raw, desc)
    new_text = f"---\n{new_fm}\n---\n{body}"
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return True, desc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any page lacks description (no writes)")
    args = ap.parse_args()

    md_files = sorted(DOCS_DIR.rglob("*.md"))
    changed = 0
    missing = 0
    skipped = 0
    samples: list[tuple[Path, str]] = []

    for f in md_files:
        text = f.read_text(encoding="utf-8")
        fm_raw, _ = split_frontmatter(text)
        if fm_raw is None:
            skipped += 1
            continue
        if has_description(fm_raw):
            continue
        if args.check:
            missing += 1
            continue
        did, desc = process_file(f, dry_run=args.dry_run)
        if did:
            changed += 1
            if len(samples) < 5:
                samples.append((f.relative_to(REPO_ROOT), desc))
        else:
            skipped += 1

    if args.check:
        print(f"scanned={len(md_files)} missing_description={missing}")
        return 1 if missing else 0

    print(f"scanned={len(md_files)} updated={changed} skipped={skipped} "
          f"dry_run={args.dry_run}")
    for path, desc in samples:
        print(f"  + {path}: {desc[:80]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
