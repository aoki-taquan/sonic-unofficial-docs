#!/usr/bin/env python3
"""Lychee-style internal link checker for the built `site/` directory.

Walks every `.html` in `site/`, collects every `<a href="...">`, and verifies
that internal targets resolve to an existing file. External `http(s)`,
`mailto:`, `tel:`, `javascript:` and pure fragment (`#foo`) links are skipped.

Writes `meta/built-links-report.md`. Returns exit 1 in `--check` mode if any
dead internal link is found.

Note: page-level structural checks (title/h1/empty tags) live in
`check_built_html.py`. This script focuses solely on link health so it can be
re-used / re-run independently in CI without paying for the full HTML parse.
"""
from __future__ import annotations

import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlparse, unquote

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = REPO_ROOT / "site"
REPORT_PATH = REPO_ROOT / "meta" / "built-links-report.md"


def _site_base_path() -> str:
    """URL path prefix from mkdocs.yml site_url (e.g. '/sonic-unofficial-docs')."""
    mk = REPO_ROOT / "mkdocs.yml"
    if not mk.exists():
        return ""
    for line in mk.read_text(encoding="utf-8").splitlines():
        if line.startswith("site_url:"):
            url = line.split(":", 1)[1].strip().strip("\"'")
            return urlparse(url).path.rstrip("/")
    return ""


SITE_BASE = _site_base_path()


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        for k, v in attrs:
            if k == "href" and v is not None:
                self.links.append(v)
                break


def resolve(page: Path, href: str) -> tuple[bool, str | None]:
    """Return (is_internal, target_path_or_None)."""
    href_nofrag, _frag = urldefrag(href)
    if not href_nofrag:
        return False, None
    parsed = urlparse(href_nofrag)
    if parsed.scheme in ("http", "https", "mailto", "tel", "ftp", "data", "javascript"):
        return False, None
    if parsed.netloc:
        return False, None
    target_str = unquote(parsed.path)
    if not target_str:
        return False, None
    if target_str.startswith("/"):
        path_only = target_str
        if SITE_BASE and path_only.startswith(SITE_BASE + "/"):
            path_only = path_only[len(SITE_BASE):]
        elif SITE_BASE and path_only == SITE_BASE:
            path_only = "/"
        target = SITE_DIR / path_only.lstrip("/")
    else:
        target = (page.parent / target_str).resolve()
    try:
        target.relative_to(SITE_DIR.resolve())
    except ValueError:
        return False, None
    if target.suffix == "":
        if target.is_dir():
            target = target / "index.html"
        else:
            cand = target.with_suffix(".html")
            if cand.exists():
                return True, str(cand)
            cand2 = target / "index.html"
            if cand2.exists():
                return True, str(cand2)
    return True, str(target)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on dead internal links (CI mode)")
    args = ap.parse_args()

    if not SITE_DIR.exists():
        sys.stderr.write(f"site/ not found at {SITE_DIR}. Run `mkdocs build` first.\n")
        return 2

    dead: list[tuple[str, str]] = []
    total_links = 0
    pages = 0

    for page in SITE_DIR.rglob("*.html"):
        pages += 1
        try:
            text = page.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        coll = LinkCollector()
        try:
            coll.feed(text)
        except Exception:
            continue
        rel = str(page.relative_to(SITE_DIR))
        for href in coll.links:
            is_internal, resolved = resolve(page, href)
            if not is_internal:
                continue
            total_links += 1
            if resolved is None or not Path(resolved).exists():
                dead.append((rel, href))

    lines = [
        "# Built HTML link-check report",
        "",
        f"Pages scanned: **{pages}**",
        f"Internal links checked: **{total_links}**",
        f"Dead internal links: **{len(dead)}**",
        "",
    ]
    if not dead:
        lines.append("_no dead internal links_")
    else:
        lines.append("## Dead internal links")
        lines.append("")
        for rel, href in dead[:500]:
            lines.append(f"- `{rel}` -> `{href}`")
        if len(dead) > 500:
            lines.append(f"- ... ({len(dead) - 500} more)")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.write(
        f"check_built_links: {pages} pages, {total_links} internal links, "
        f"{len(dead)} dead. Report: {REPORT_PATH.relative_to(REPO_ROOT)}\n"
    )
    if args.check and dead:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
