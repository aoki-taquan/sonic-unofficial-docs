#!/usr/bin/env python3
"""Inject glossary links into docs/**/*.md.

For every term defined in ``docs/reference/glossary.md`` (i.e. lines of the
form ``### <Term> {#term-<slug>}``), find the **first occurrence** of the term
in each other Markdown page's body and replace it with a Markdown link to the
glossary anchor.  All later occurrences on the same page are left untouched.

The injection is conservative:

* Frontmatter, code blocks (fenced and indented), and HTML comments are skipped.
* ATX/Setext headings are skipped.
* Lines inside already-rendered evidence blocks (``<!-- evidence-rendered:start
  -->`` ... ``<!-- evidence-rendered:end -->``) are skipped.
* Existing Markdown links / link text are skipped (we never inject inside a
  ``[...](...)`` construct).
* Terms that look "too generic" (very short Japanese strings or common
  katakana noise words) are excluded via ``STOPLIST``.  Short ASCII acronyms
  (BGP, ACL, RIB, ...) are explicitly allowed via ``ALLOW_SHORT``.

Idempotency: every touched file gets a trailing comment
``<!-- glossary-links-injected: <sha1> -->`` whose payload is the sha1 of the
sorted list of (term, anchor) pairs that were injected.  Re-running with the
same glossary contents is a no-op.

Modes
-----
default   Rewrite drifted files in place. Print summary. Exit 0.
--check   Report drift only. Exit 1 if any file would change.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
GLOSSARY = DOCS / "reference" / "glossary.md"
MARKER_PREFIX = "<!-- glossary-links-injected:"
MARKER_RE = re.compile(r"<!-- glossary-links-injected: ([0-9a-f]+) -->")

HEADING_RE = re.compile(r"^(###\s+)(.+?)(\s*\{#(term-[A-Za-z0-9._-]+)\})\s*$")

# Words to exclude even though they appear as glossary terms.  These are too
# generic in running Japanese text and would create excessive noise links.
# (Currently the glossary has no entries that match these strings, but the
# list is here as a guardrail for future additions.)
STOPLIST: set[str] = {
    "ルーティング",
    "インタフェース",
    "インターフェース",
    "設定",
    "ポート",
    "リンク",
    "イベント",
    "メッセージ",
    "テーブル",
    "プロトコル",
}

# Short (<= 3 char) ASCII terms are normally too ambiguous to auto-link, so we
# require an explicit allow-list.  Anything not listed here that is <= 3 chars
# (e.g. "VS") is skipped.
ALLOW_SHORT: set[str] = {
    "AAA", "ACL", "ARP", "BFD", "BGP", "CRM", "DPB", "DPU",
    "FDB", "FPM", "FRR", "GCU", "HLD", "INT", "LAG", "MUX",
    "NAT", "NDP", "NPU", "PFC", "RIF", "QoS", "SAI", "TAM",
    "VRF", "VOQ", "WRED", "ZTP", "ENI", "MPLS",
}


def parse_frontmatter(text: str) -> tuple[str, str]:
    m = re.match(r"^(---\s*\n.*?\n---\s*\n)", text, re.DOTALL)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def collect_terms() -> list[tuple[str, str]]:
    """Return [(term, anchor)] in document order, deduped."""
    text = GLOSSARY.read_text(encoding="utf-8")
    _fm, body = parse_frontmatter(text)
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for line in body.splitlines():
        m = HEADING_RE.match(line)
        if not m:
            continue
        term = m.group(2).strip()
        anchor = m.group(4)
        # Skip composite-name entries like "natmgrd / natsyncd": they would
        # never match verbatim in prose.  Pick the first component instead.
        if " / " in term:
            term = term.split(" / ", 1)[0].strip()
        if term in seen:
            continue
        if term in STOPLIST:
            continue
        # Length / character-set filters.
        ascii_only = all(ord(c) < 128 for c in term)
        if ascii_only and len(term) <= 3 and term not in ALLOW_SHORT:
            continue
        if len(term) < 2:
            continue
        seen.add(term)
        out.append((term, anchor))
    # Sort longer terms first so e.g. "EVPN-MH" is preferred over "EVPN" when
    # both could match the same text starting position.
    out.sort(key=lambda x: (-len(x[0]), x[0]))
    return out


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^(\s*)(```|~~~)")
EVIDENCE_OPEN = "<!-- evidence-rendered:start -->"
EVIDENCE_CLOSE = "<!-- evidence-rendered:end -->"
HTML_COMMENT_OPEN_RE = re.compile(r"<!--")
HTML_COMMENT_CLOSE_RE = re.compile(r"-->")


def rel_glossary_link(page_rel: str, anchor: str) -> str:
    """Return relative path from `docs/<page_rel>` to glossary, with anchor."""
    page = Path(page_rel)
    # Depth of the page from docs/ (number of parent directories).
    depth = len(page.parts) - 1
    if depth == 0:
        prefix = "./"
    else:
        prefix = "../" * depth
    return f"{prefix}reference/glossary.md#{anchor}"


def _line_is_eligible(line: str) -> bool:
    """Cheap pre-filter: a line that is a heading / blockquote-only / blank
    cannot host an injection."""
    stripped = line.lstrip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return False
    if stripped.startswith("<!--"):
        return False
    # Lines that are just an admonition declaration (``??? note "..."``).
    if stripped.startswith("???") or stripped.startswith("!!!"):
        return False
    return True


def _mask_protected_spans(line: str) -> list[tuple[int, int]]:
    """Return list of (start, end) char ranges within ``line`` where injection
    is forbidden: existing markdown links, inline code, and raw HTML tags."""
    spans: list[tuple[int, int]] = []
    # Inline code: `...` (non-greedy, single line).
    for m in re.finditer(r"`[^`]+`", line):
        spans.append((m.start(), m.end()))
    # Markdown links: [text](target) and ![alt](target).
    for m in re.finditer(r"!?\[[^\]]*\]\([^)]*\)", line):
        spans.append((m.start(), m.end()))
    # Reference-style links: [text][ref].
    for m in re.finditer(r"\[[^\]]+\]\[[^\]]*\]", line):
        spans.append((m.start(), m.end()))
    # Raw HTML tags.
    for m in re.finditer(r"<[^>]+>", line):
        spans.append((m.start(), m.end()))
    return spans


def _in_span(pos: int, end: int, spans: list[tuple[int, int]]) -> bool:
    for s, e in spans:
        if pos < e and end > s:
            return True
    return False


def process_file(
    path: Path,
    terms: list[tuple[str, str]],
) -> tuple[str, int, list[tuple[str, str]]]:
    """Return (new_text, injected_count, injected_pairs)."""
    original = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(original)
    rel = path.relative_to(DOCS).as_posix()

    # Strip any pre-existing marker line so we can recompute it.
    body_stripped = re.sub(
        r"\n*<!-- glossary-links-injected: [0-9a-f]+ -->\s*$",
        "",
        body,
    )

    lines = body_stripped.splitlines()

    # Pre-compute per-line state: in-fence, in-evidence-rendered, in-html-comment.
    in_fence = False
    fence_marker = ""
    in_evidence = False
    in_html_comment = False
    eligible: list[bool] = []
    for line in lines:
        line_eligible = True
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(2)
            if not in_fence:
                in_fence = True
                fence_marker = marker
                line_eligible = False
            elif fence_marker == marker:
                in_fence = False
                line_eligible = False
            else:
                line_eligible = False
        elif in_fence:
            line_eligible = False
        # Indented code block (4-space indent on otherwise blank line section)
        # is hard to detect without state; approximate by treating any line
        # starting with 4 spaces or a tab that is *not* a list continuation as
        # code.  Safer to just skip.
        if line_eligible and (line.startswith("    ") or line.startswith("\t")):
            # Heuristic: if the line is part of an admonition body (preceded by
            # an admonition declaration) we still skip it -- this conveniently
            # excludes the rendered evidence excerpt blocks.
            line_eligible = False

        if EVIDENCE_OPEN in line:
            in_evidence = True
            line_eligible = False
        if in_evidence:
            line_eligible = False
        if EVIDENCE_CLOSE in line:
            in_evidence = False
            line_eligible = False

        # HTML comment tracking (multi-line).
        if in_html_comment:
            line_eligible = False
            if HTML_COMMENT_CLOSE_RE.search(line):
                in_html_comment = False
        else:
            opens = len(HTML_COMMENT_OPEN_RE.findall(line))
            closes = len(HTML_COMMENT_CLOSE_RE.findall(line))
            if opens > closes:
                in_html_comment = True
                line_eligible = False
            elif opens > 0 and opens == closes:
                # Self-contained comment line: still skip.
                line_eligible = False

        if line_eligible and not _line_is_eligible(line):
            line_eligible = False

        eligible.append(line_eligible)

    # First-occurrence injection per term.
    remaining = {term: anchor for term, anchor in terms}

    # If a term is *already* linked to its glossary anchor anywhere in the
    # body, suppress further injection for that term (idempotency: a previous
    # run already handled it; do not chase later occurrences).
    full_body = "\n".join(lines)
    for term, anchor in list(remaining.items()):
        # Match [<term>](...#<anchor>) loosely.
        pat = re.compile(
            r"\[" + re.escape(term) + r"\]\([^)]*#" + re.escape(anchor) + r"\)"
        )
        if pat.search(full_body):
            del remaining[term]

    injected_pairs: list[tuple[str, str]] = []
    new_lines = list(lines)
    injected_count = 0

    # Iterate lines, then terms; we want the *earliest* occurrence per term,
    # so scan line-by-line and at each line try every remaining term.
    for idx, line in enumerate(new_lines):
        if not eligible[idx]:
            continue
        if not remaining:
            break
        # Recompute protected spans lazily.
        spans = _mask_protected_spans(line)
        # Try terms in order longest-first to avoid nested substring conflicts.
        for term in sorted(remaining.keys(), key=lambda t: (-len(t), t)):
            anchor = remaining[term]
            # Find earliest occurrence not in a protected span.
            search_from = 0
            found_pos = -1
            while True:
                p = line.find(term, search_from)
                if p < 0:
                    break
                if not _in_span(p, p + len(term), spans):
                    found_pos = p
                    break
                search_from = p + 1
            if found_pos < 0:
                continue
            # Word-boundary heuristic for ASCII-only terms to avoid linking
            # inside identifiers like "BGPSESSION" or "ACL_TABLE".
            ascii_only = all(ord(c) < 128 for c in term)
            if ascii_only:
                before = line[found_pos - 1] if found_pos > 0 else ""
                after_idx = found_pos + len(term)
                after = line[after_idx] if after_idx < len(line) else ""
                def _wordy(ch: str) -> bool:
                    return ch.isalnum() or ch == "_"
                if (before and _wordy(before)) or (after and _wordy(after)):
                    continue
            link = f"[{term}]({rel_glossary_link(rel, anchor)})"
            line = line[:found_pos] + link + line[found_pos + len(term):]
            new_lines[idx] = line
            # Refresh protected spans after mutation.
            spans = _mask_protected_spans(line)
            injected_pairs.append((term, anchor))
            injected_count += 1
            del remaining[term]
            if not remaining:
                break

    if injected_count == 0:
        # No new injections.  Preserve existing file content verbatim so that
        # a re-run is a true no-op (idempotent).  If the previous marker is
        # somehow stale, it will be refreshed only when a new injection
        # actually occurs.
        return original, 0, []

    payload = ",".join(f"{t}:{a}" for t, a in sorted(injected_pairs))
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    marker = f"<!-- glossary-links-injected: {digest} -->"

    new_body = "\n".join(new_lines).rstrip() + "\n\n" + marker + "\n"
    return fm + new_body, injected_count, injected_pairs


def iter_target_files() -> list[Path]:
    out: list[Path] = []
    for p in sorted(DOCS.rglob("*.md")):
        rel = p.relative_to(DOCS).as_posix()
        if rel == "reference/glossary.md":
            continue
        if rel.startswith("reference/glossary/"):
            continue
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if drift")
    ap.add_argument(
        "--verbose", "-v", action="store_true", help="print per-file injection counts"
    )
    args = ap.parse_args()

    terms = collect_terms()
    if not terms:
        print("warning: no glossary terms collected", file=sys.stderr)
        return 0

    total_files = 0
    total_links = 0
    drift_files: list[Path] = []

    for path in iter_target_files():
        original = path.read_text(encoding="utf-8")
        new_text, count, _pairs = process_file(path, terms)
        if new_text != original:
            drift_files.append(path)
            total_files += 1
            total_links += count
            if not args.check:
                path.write_text(new_text, encoding="utf-8")
                if args.verbose:
                    print(f"  {path.relative_to(ROOT)}: +{count}")

    if args.check:
        if drift_files:
            for p in drift_files:
                print(f"drift: {p.relative_to(ROOT)}", file=sys.stderr)
            print(
                f"\n{len(drift_files)} file(s) would change "
                f"({total_links} link(s) would be injected). "
                f"Run `python3 meta/scripts/inject_glossary_links.py`.",
                file=sys.stderr,
            )
            return 1
        return 0

    print(
        f"glossary inject: updated {total_files} file(s), "
        f"injected {total_links} link(s) total."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
