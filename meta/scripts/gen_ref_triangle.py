#!/usr/bin/env python3
"""Generate sibling triangle links (YANG ↔ CONFIG_DB ↔ CLI) in Reference pages.

For each docs/reference/{yang,config-db,cli}/*.md page, read the frontmatter's
`related:` block (config_db / cli / yang lists) and append a marker-bounded
"## 関連リファレンス" section near the end of the page (just before the first
"## 引用元" heading, or at EOF).

Existing manually-written "## 関連ページ" sections are left untouched.

Re-runnable: anything between <!-- ref-triangle:start --> and
<!-- ref-triangle:end --> is regenerated each invocation.

frontmatter is NOT modified.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "docs" / "reference"

START = "<!-- ref-triangle:start -->"
END = "<!-- ref-triangle:end -->"

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = s.replace("_", "-").replace(" ", "-").replace("/", "-")
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def parse_related(fm_text: str) -> dict[str, list[str]]:
    """Very small purpose-built parser for the `related:` block."""
    out: dict[str, list[str]] = {"config_db": [], "cli": [], "yang": []}
    lines = fm_text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].rstrip() == "related:":
            i += 1
            current: str | None = None
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t") or lines[i] == ""):
                line = lines[i]
                if line == "":
                    i += 1
                    continue
                # match "  key: ..." with 2-space indent
                m = re.match(r"^  ([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
                if m:
                    key = m.group(1)
                    rest = m.group(2).strip()
                    current = key if key in out else None
                    if current and rest:
                        # inline form, e.g. [A, B] or "[A]" or '"a", "b"'
                        if rest.startswith("[") and rest.endswith("]"):
                            inner = rest[1:-1]
                            items = [
                                x.strip().strip('"').strip("'")
                                for x in inner.split(",")
                                if x.strip()
                            ]
                            out[current].extend(items)
                        elif rest not in ("[]", ""):
                            # bare scalar
                            out[current].append(rest.strip('"').strip("'"))
                    i += 1
                    continue
                m2 = re.match(r"^    - (.+)$", line)
                if m2 and current:
                    val = m2.group(1).strip().strip('"').strip("'")
                    out[current].append(val)
                    i += 1
                    continue
                # something else under frontmatter; stop the related block
                break
            return out
        i += 1
    return out


def build_index(area: str) -> set[str]:
    d = REF / area
    if not d.is_dir():
        return set()
    return {p.stem for p in d.glob("*.md") if p.stem != "index"}


def render_link(area_from: str, area_to: str, name: str, index: set[str]) -> str:
    slug = slugify(name)
    if slug in index:
        # relative path from area_from to area_to
        if area_from == area_to:
            rel = f"{slug}.md"
        else:
            rel = f"../{area_to}/{slug}.md"
        return f"[`{name}`]({rel})"
    return f"`{name}`"


AREA_DIR = {"yang": "yang", "config_db": "config-db", "cli": "cli"}
AREA_LABEL = {"yang": "YANG", "config_db": "CONFIG_DB", "cli": "CLI"}


def render_block(area_from: str, related: dict[str, list[str]], indexes: dict[str, set[str]]) -> str:
    """Render the triangle block content (between markers, exclusive)."""
    # The two sibling areas (not self)
    self_key = {"yang": "yang", "config-db": "config_db", "cli": "cli"}[area_from]
    sibling_keys = [k for k in ("yang", "config_db", "cli") if k != self_key]

    lines: list[str] = ["", "## 関連リファレンス", ""]
    any_item = False
    for k in sibling_keys:
        items = []
        seen = set()
        for name in related.get(k, []):
            if not name or name in seen:
                continue
            seen.add(name)
            items.append(name)
        if not items:
            continue
        any_item = True
        area_to = AREA_DIR[k]
        rendered = [render_link(area_from, area_to, n, indexes[area_to]) for n in items]
        lines.append(f"- {AREA_LABEL[k]}: " + " / ".join(rendered))
    if not any_item:
        lines.append("- (関連リンクなし)")
    lines.append("")
    return "\n".join(lines)


BLOCK_RE = re.compile(
    re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.DOTALL
)


def insert_block(body: str, block: str) -> str:
    """Insert/replace the marker block in the page body (after frontmatter)."""
    wrapped = f"{START}\n{block}\n{END}\n"

    if START in body and END in body:
        return BLOCK_RE.sub(wrapped, body, count=1)

    # Find first "## 引用元" heading and insert before it
    m = re.search(r"^## 引用元\s*$", body, re.MULTILINE)
    if m:
        idx = m.start()
        # ensure trailing newline before block
        prefix = body[:idx].rstrip() + "\n\n"
        suffix = body[idx:]
        return prefix + wrapped + "\n" + suffix
    # fallback: append at EOF
    return body.rstrip() + "\n\n" + wrapped


def process_file(p: Path, area_from: str, indexes: dict[str, set[str]]) -> int:
    """Return number of links rendered (0 or more)."""
    text = p.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return 0
    fm = m.group(1)
    related = parse_related(fm)
    # count sibling links (links only, not includes self)
    self_key = {"yang": "yang", "config-db": "config_db", "cli": "cli"}[area_from]
    n_links = sum(len(related.get(k, [])) for k in ("yang", "config_db", "cli") if k != self_key)

    block_inner = render_block(area_from, related, indexes)
    body_before = text
    body_after = insert_block(body_before, block_inner)
    if body_after != body_before:
        p.write_text(body_after, encoding="utf-8")
    return n_links


def main() -> int:
    indexes = {
        "yang": build_index("yang"),
        "config-db": build_index("config-db"),
        "cli": build_index("cli"),
    }
    total_pages = 0
    total_links = 0
    for area in ("yang", "config-db", "cli"):
        d = REF / area
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            if p.stem == "index":
                continue
            n = process_file(p, area, indexes)
            total_pages += 1
            total_links += n
    print(f"processed pages: {total_pages}")
    print(f"sibling links rendered: {total_links}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
