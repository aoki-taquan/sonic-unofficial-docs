#!/usr/bin/env python3
"""Lint docs/ for fenced code blocks missing a language tag.

MkDocs Material's PyMdown ``superfences`` renders untagged code blocks as
plain text, losing syntax highlight. This script scans docs/**/*.md for
``` blocks (with empty info string) and:

1. ``--report``: print human-readable summary (count by detected language)
2. ``--fix``: rewrite the opening fence to include the detected language
   tag. Blocks with no confident guess are tagged ``text``.
3. ``--check``: CI informational mode — always exit 0.

Detection heuristics (best-effort, conservative — when uncertain → text):

- ``#!/bin/bash``, ``$ ``, ``sudo ``, ``apt ``, ``docker ``, ``redis-cli``,
  ``show `` → bash
- starts with ``{`` and contains many ``"`` → json
- ``key:`` indent style (yaml-ish, no curly braces) → yaml
- ``def ``, ``import ``, ``print(`` → python
- ``#include`` → c
- else → text

Frontmatter is skipped. Nested fences inside ``~~~`` are handled.

Exit codes:
    0  always for --check; otherwise 0 if no untagged blocks remain
       (after a successful --fix run also 0).
    1  default mode when untagged blocks exist and --fix not given.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

FENCE_OPEN_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>```|~~~)(?P<info>.*)$")


def detect_lang(body: str) -> str:
    """Return one of bash / yaml / json / python / c / sh / text."""
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if not lines:
        return "text"
    first = lines[0].lstrip()
    joined = "\n".join(lines)

    # shebang
    if first.startswith("#!/bin/bash") or first.startswith("#!/usr/bin/env bash"):
        return "bash"
    if first.startswith("#!/bin/sh") or first.startswith("#!/usr/bin/env sh"):
        return "sh"

    # C / C++ headers
    if re.search(r"^#include\s*[<\"]", joined, re.MULTILINE):
        return "c"

    # Python signatures
    py_hits = 0
    if re.search(r"^\s*def\s+\w+\s*\(", joined, re.MULTILINE):
        py_hits += 1
    if re.search(r"^\s*import\s+\w+", joined, re.MULTILINE):
        py_hits += 1
    if re.search(r"^\s*from\s+\w+\s+import\s+", joined, re.MULTILINE):
        py_hits += 1
    if re.search(r"\bprint\s*\(", joined):
        py_hits += 1
    if py_hits >= 1 and "{" not in first:
        # avoid mistaking pseudo-code blocks; require a real Python signature
        if re.search(r"^\s*(def|import|from)\s", joined, re.MULTILINE):
            return "python"

    # JSON: starts with { or [, lots of double quotes, no shell prompts
    stripped = joined.strip()
    if (stripped.startswith("{") or stripped.startswith("[")) and stripped.count('"') >= 2:
        if not re.search(r"^\s*[#\$]\s", joined, re.MULTILINE):
            # quick balance heuristic
            if stripped.endswith("}") or stripped.endswith("]"):
                return "json"

    # Bash: prompts and common admin commands
    bash_patterns = [
        r"^\s*\$\s+",
        r"^\s*#\s*\w+",  # comment lines hint at scripts, weak
        r"\bsudo\s+",
        r"\bapt(-get)?\s+",
        r"\bdocker\s+",
        r"\bredis-cli\b",
        r"\bsystemctl\s+",
        r"\bshow\s+\w+",
        r"\bconfig\s+\w+",
        r"\bsonic-cli\b",
        r"\bping\s+",
        r"\biptables\s+",
    ]
    bash_score = 0
    for pat in bash_patterns:
        if re.search(pat, joined, re.MULTILINE):
            bash_score += 1
    # exclude weak-comment-only score
    if bash_score >= 1 and (
        re.search(r"^\s*\$\s+", joined, re.MULTILINE)
        or re.search(r"\b(sudo|apt|apt-get|docker|redis-cli|systemctl|show|config|sonic-cli|ping|iptables)\b", joined)
    ):
        return "bash"

    # YAML: key: value lines, no braces dominance
    yaml_keys = len(re.findall(r"^\s*[A-Za-z_][\w\-]*\s*:(\s|$)", joined, re.MULTILINE))
    if yaml_keys >= 2 and stripped.count("{") <= 1 and not stripped.startswith("{"):
        return "yaml"

    return "text"


def parse_blocks(text: str):
    """Yield (open_line_idx, close_line_idx, marker, info, body) tuples
    for each fenced block outside frontmatter."""
    lines = text.splitlines()
    i = 0
    # skip frontmatter
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines):
            if lines[i].strip() == "---":
                i += 1
                break
            i += 1
    while i < len(lines):
        m = FENCE_OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        marker = m.group("marker")
        info = m.group("info")
        open_idx = i
        j = i + 1
        body_lines = []
        while j < len(lines):
            m2 = FENCE_OPEN_RE.match(lines[j])
            if m2 and m2.group("marker") == marker and m2.group("info").strip() == "":
                # closing fence (no info string)
                break
            body_lines.append(lines[j])
            j += 1
        if j >= len(lines):
            # unterminated — bail
            break
        yield (open_idx, j, marker, info, "\n".join(body_lines))
        i = j + 1


def process_file(path: Path, fix: bool):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=False)
    blocks = list(parse_blocks(text))
    untagged = []
    for (oi, ci, marker, info, body) in blocks:
        if info.strip() == "":
            lang = detect_lang(body)
            untagged.append((oi, ci, marker, lang, body))

    if fix and untagged:
        # rewrite from bottom up to keep line indices stable
        for (oi, ci, marker, lang, body) in reversed(untagged):
            orig = lines[oi]
            m = FENCE_OPEN_RE.match(orig)
            indent = m.group("indent")
            lines[oi] = f"{indent}{marker}{lang}"
        new_text = "\n".join(lines)
        if text.endswith("\n") and not new_text.endswith("\n"):
            new_text += "\n"
        path.write_text(new_text, encoding="utf-8")

    return untagged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", action="store_true",
                        help="Print human report")
    parser.add_argument("--fix", action="store_true",
                        help="Rewrite opening fences with detected language")
    parser.add_argument("--check", action="store_true",
                        help="CI informational mode (always exit 0)")
    args = parser.parse_args()

    files = sorted(DOCS_DIR.rglob("*.md"))
    total = 0
    by_lang: Counter = Counter()
    files_with = 0
    per_file_report: list[tuple[Path, int, Counter]] = []

    for path in files:
        try:
            untagged = process_file(path, fix=args.fix)
        except Exception as exc:
            print(f"! could not parse {path}: {exc}", file=sys.stderr)
            continue
        if not untagged:
            continue
        files_with += 1
        total += len(untagged)
        file_counter: Counter = Counter()
        for (_oi, _ci, _mk, lang, _body) in untagged:
            by_lang[lang] += 1
            file_counter[lang] += 1
        per_file_report.append((path, len(untagged), file_counter))

    print("# Untagged fenced code-block lint")
    print()
    print(f"Total untagged blocks: {total} across {files_with} files")
    if by_lang:
        print()
        print("## Detected language distribution")
        for lang, n in by_lang.most_common():
            print(f"- {lang}: {n}")

    if args.report:
        print()
        print("## Per-file breakdown")
        for path, n, fc in per_file_report:
            rel = path.relative_to(REPO_ROOT)
            dist = ", ".join(f"{k}={v}" for k, v in fc.most_common())
            print(f"- {rel}: {n} ({dist})")

    if args.fix:
        print()
        print(f"Fix mode: rewrote {total} fences.")

    if args.check:
        return 0
    return 1 if total and not args.fix else 0


if __name__ == "__main__":
    sys.exit(main())
