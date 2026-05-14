#!/usr/bin/env python3
"""Check the built `site/` directory for visual / structural HTML issues.

This script walks every `.html` page produced by `mkdocs build` and reports
issues that would surface as visually broken pages to a reader:

- missing `<title>` tag
- 0 or >1 `<h1>` per page
- empty `<a href="">`
- empty `<img src="">`
- empty `<pre><code>` blocks
- mermaid placeholder (`class="mermaid"` containing raw text) with no rendered
  SVG sibling (warning only; mermaid renders client-side so absence is normal —
  we only flag if the source block is itself empty)
- very long single lines (>2000 chars without a break) — horizontal overflow
- broken `<details>` / `<summary>` nesting

It also performs internal link-checking: every `<a href="...">` that points to
another site-internal page must resolve to an existing `.html` (or `index.html`
under a directory). External `http(s)` and `mailto:` links are skipped.

Outputs:
- `meta/built-html-report.md` (always)
- exit 1 in `--check` mode when high-priority issues (dead internal links,
  empty `<a>`/`<img>`, duplicate or missing `<h1>`) exist.

Usage:
  python3 meta/scripts/check_built_html.py
  python3 meta/scripts/check_built_html.py --check
"""
from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlparse, unquote

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = REPO_ROOT / "site"
REPORT_PATH = REPO_ROOT / "meta" / "built-html-report.md"


def _site_base_path() -> str:
    """URL path prefix from mkdocs.yml site_url (e.g. '/sonic-unofficial-docs').

    Absolute hrefs in the built HTML start with this prefix, so we must strip
    it before mapping back to a file under site/.
    """
    mk = REPO_ROOT / "mkdocs.yml"
    if not mk.exists():
        return ""
    for line in mk.read_text(encoding="utf-8").splitlines():
        if line.startswith("site_url:"):
            url = line.split(":", 1)[1].strip().strip("\"'")
            return urlparse(url).path.rstrip("/")
    return ""


SITE_BASE = _site_base_path()

# Long-line threshold for horizontal-overflow detection.
LONG_LINE_THRESHOLD = 2000

# Skip these site paths (search index, sitemap shells, redirect stubs).
SKIP_NAMES = {"sitemap.xml", "search_index.json"}


class PageParser(HTMLParser):
    """Collect structural info per HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_present = False
        self._in_title = False
        self.h1_count = 0
        self.empty_a = 0
        self.empty_img = 0
        self.empty_pre_code = 0
        self._pre_code_stack: list[list[str]] = []
        self.mermaid_empty = 0
        self._in_mermaid: int | None = None
        self._mermaid_buf: list[str] = []
        self.details_open = 0
        self.summary_mismatch = 0
        self._details_stack: list[int] = []  # depth-style track
        self.links: list[str] = []  # all href values for link-check

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "title":
            self._in_title = True
            self.title_present = True
        elif tag == "h1":
            # Only count h1 inside main article content; mkdocs material puts
            # one in the page header. We count all and treat >1 in the *main*
            # article as suspect, but a global count works as proxy: most pages
            # have exactly one h1 (the article title). Pages with 0 or >1 are
            # flagged.
            self.h1_count += 1
        elif tag == "a":
            href = attrs_d.get("href")
            if href is not None:
                if href.strip() == "":
                    self.empty_a += 1
                else:
                    self.links.append(href)
            # Some material themes emit <a> without href for icon-only anchors;
            # those are not flagged (href is None).
        elif tag == "img":
            src = attrs_d.get("src")
            if src is not None and src.strip() == "":
                self.empty_img += 1
        elif tag == "pre":
            self._pre_code_stack.append([])
        elif tag == "code" and self._pre_code_stack:
            # we'll capture data through handle_data
            pass
        elif tag == "div" and "mermaid" in (attrs_d.get("class") or "").split():
            self._in_mermaid = 0
            self._mermaid_buf = []
        elif tag == "details":
            self._details_stack.append(0)
        elif tag == "summary":
            if not self._details_stack:
                self.summary_mismatch += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "pre":
            if self._pre_code_stack:
                buf = self._pre_code_stack.pop()
                if not any(s.strip() for s in buf):
                    self.empty_pre_code += 1
        elif tag == "div" and self._in_mermaid is not None:
            text = "".join(self._mermaid_buf).strip()
            if not text:
                self.mermaid_empty += 1
            self._in_mermaid = None
            self._mermaid_buf = []
        elif tag == "details":
            if self._details_stack:
                self._details_stack.pop()
            else:
                self.details_open += 1  # closing without opening

    def handle_data(self, data):
        if self._pre_code_stack:
            self._pre_code_stack[-1].append(data)
        if self._in_mermaid is not None:
            self._mermaid_buf.append(data)


def resolve_internal_link(page: Path, href: str) -> tuple[bool, str | None]:
    """Return (is_internal, resolved_path_or_None).

    is_internal=False for external / mailto / javascript / fragment-only.
    resolved_path is the absolute path to the .html file the link should
    resolve to (or None if we determined the target should exist but couldn't
    locate it; in that case the caller treats it as broken).
    """
    href_nofrag, _frag = urldefrag(href)
    if not href_nofrag:
        return False, None  # pure fragment
    parsed = urlparse(href_nofrag)
    if parsed.scheme in ("http", "https", "mailto", "tel", "ftp", "data", "javascript"):
        return False, None
    if parsed.netloc:
        return False, None

    target_str = unquote(parsed.path)
    if not target_str:
        return False, None

    if target_str.startswith("/"):
        # MkDocs absolute hrefs are prefixed with the site_url path (e.g.
        # `/sonic-unofficial-docs/...`). Strip that prefix before mapping
        # back to site/.
        path_only = target_str
        if SITE_BASE and path_only.startswith(SITE_BASE + "/"):
            path_only = path_only[len(SITE_BASE):]
        elif SITE_BASE and path_only == SITE_BASE:
            path_only = "/"
        target = SITE_DIR / path_only.lstrip("/")
    else:
        target = (page.parent / target_str).resolve()

    # Stay inside site/
    try:
        target.relative_to(SITE_DIR.resolve())
    except ValueError:
        return False, None

    if target.suffix == "":
        # Directory-style URL → index.html
        if target.is_dir():
            target = target / "index.html"
        else:
            # Maybe trailing slash got stripped; try .html
            cand = target.with_suffix(".html")
            if cand.exists():
                return True, str(cand)
            cand2 = target / "index.html"
            if cand2.exists():
                return True, str(cand2)
    return True, str(target)


def check_long_lines(html_text: str) -> int:
    count = 0
    for line in html_text.split("\n"):
        if len(line) > LONG_LINE_THRESHOLD:
            count += 1
    return count


def walk_site() -> dict:
    report: dict = {
        "pages_checked": 0,
        "missing_title": [],
        "h1_zero": [],
        "h1_many": [],
        "empty_a": [],
        "empty_img": [],
        "empty_pre_code": [],
        "mermaid_empty": [],
        "long_lines": [],
        "details_broken": [],
        "dead_links": [],  # (page, href)
    }

    html_files = [
        p
        for p in SITE_DIR.rglob("*.html")
        if p.name not in SKIP_NAMES
    ]
    report["pages_checked"] = len(html_files)

    for page in html_files:
        try:
            text = page.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parser = PageParser()
        try:
            parser.feed(text)
        except Exception:
            # malformed HTML; record as details_broken proxy
            report["details_broken"].append(str(page.relative_to(SITE_DIR)))
            continue

        rel = str(page.relative_to(SITE_DIR))
        if not parser.title_present:
            report["missing_title"].append(rel)
        if parser.h1_count == 0:
            report["h1_zero"].append(rel)
        elif parser.h1_count > 1:
            report["h1_many"].append((rel, parser.h1_count))
        if parser.empty_a:
            report["empty_a"].append((rel, parser.empty_a))
        if parser.empty_img:
            report["empty_img"].append((rel, parser.empty_img))
        if parser.empty_pre_code:
            report["empty_pre_code"].append((rel, parser.empty_pre_code))
        if parser.mermaid_empty:
            report["mermaid_empty"].append((rel, parser.mermaid_empty))
        if parser.details_open or parser.summary_mismatch:
            report["details_broken"].append(rel)

        long_n = check_long_lines(text)
        if long_n:
            report["long_lines"].append((rel, long_n))

        # Internal link check
        for href in parser.links:
            is_internal, resolved = resolve_internal_link(page, href)
            if not is_internal:
                continue
            if resolved is None or not Path(resolved).exists():
                report["dead_links"].append((rel, href))

    return report


def write_report(report: dict) -> None:
    lines = ["# Built HTML quality report", ""]
    lines.append(f"Pages checked: **{report['pages_checked']}**")
    lines.append("")

    sections = [
        ("Missing <title>", report["missing_title"], "high"),
        ("Pages with 0 <h1>", report["h1_zero"], "high"),
        ("Pages with >1 <h1>", report["h1_many"], "high"),
        ("Empty <a href=''>", report["empty_a"], "high"),
        ("Empty <img src=''>", report["empty_img"], "high"),
        ("Empty <pre><code>", report["empty_pre_code"], "medium"),
        ("Mermaid empty placeholder", report["mermaid_empty"], "low"),
        ("Very long single line (>2000 chars)", report["long_lines"], "medium"),
        ("Broken <details>/<summary>", report["details_broken"], "high"),
        ("Dead internal links", report["dead_links"], "high"),
    ]
    for title, items, sev in sections:
        lines.append(f"## {title}  _(severity: {sev})_")
        lines.append("")
        if not items:
            lines.append("_none_")
        else:
            lines.append(f"Count: **{len(items)}**")
            lines.append("")
            for item in items[:200]:
                if isinstance(item, tuple):
                    lines.append(f"- `{item[0]}` — {item[1]}")
                else:
                    lines.append(f"- `{item}`")
            if len(items) > 200:
                lines.append(f"- ... ({len(items) - 200} more)")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def high_priority_count(report: dict) -> int:
    return (
        len(report["missing_title"])
        + len(report["h1_zero"])
        + len(report["h1_many"])
        + len(report["empty_a"])
        + len(report["empty_img"])
        + len(report["details_broken"])
        + len(report["dead_links"])
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on high-priority issues (CI mode)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on ANY issue (including informational)")
    args = ap.parse_args()

    if not SITE_DIR.exists():
        sys.stderr.write(
            f"site/ not found at {SITE_DIR}. Run `mkdocs build` first.\n"
        )
        return 2

    report = walk_site()
    write_report(report)

    hi = high_priority_count(report)
    sys.stdout.write(
        f"check_built_html: {report['pages_checked']} pages, "
        f"{hi} high-priority issues. Report: {REPORT_PATH.relative_to(REPO_ROOT)}\n"
    )

    if args.strict:
        any_issue = hi + len(report["empty_pre_code"]) + len(report["mermaid_empty"]) + len(report["long_lines"])
        return 1 if any_issue else 0
    if args.check:
        return 1 if hi else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
