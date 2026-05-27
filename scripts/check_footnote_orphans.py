#!/usr/bin/env python3
"""
Detect orphan footnote definitions in docs/**/*.md.

An orphan is a [^N]: definition that has no corresponding [^N] reference in
the same file. This script distinguishes two reference forms:

  1. Normal ref:  [^N] not followed by ':'    (e.g. "詳細は[^1]。")
  2. Inline ref:  [^N]: NOT at line-start     (e.g. "ポイント[^1]:\n\n- ...")

Form 2 is a Japanese document pattern where [^N] introduces a list via ':'.
The naive regex ``r'\\[\\^(\\w+)\\](?!:)'`` misses form 2, causing false positives.
This script handles both forms correctly.

Usage:
    python3 scripts/check_footnote_orphans.py [--verbose]

Exit code:
    0 = no orphans found
    1 = orphans found (names printed to stdout)
"""

import re
import sys
from pathlib import Path


def find_orphan_defs(docs_root: Path, verbose: bool = False):
    orphans = []
    for f in sorted(docs_root.rglob("*.md")):
        # Skip meta/verification pages
        if "verification" in f.parts:
            continue
        t = f.read_text(encoding="utf-8", errors="replace")

        # Definitions: line starts with [^key]:
        defs = set(re.findall(r"^\[\^(\w+)\]:", t, re.MULTILINE))

        # References form 1: [^key] NOT followed by ':'
        refs_normal = set(re.findall(r"\[\^(\w+)\](?!:)", t))

        # References form 2: [^key]: where the '[' is NOT at line start
        # (inline usage like "ポイント[^1]:" introducing a list)
        refs_inline = set(re.findall(r"[^\n]\[\^(\w+)\]:", t))

        refs = refs_normal | refs_inline
        orph = defs - refs
        if orph:
            orphans.append((str(f), orph))
            if verbose:
                for key in sorted(orph):
                    # Show definition line
                    for i, line in enumerate(t.splitlines(), 1):
                        if re.match(rf"^\[\^{re.escape(key)}\]:", line):
                            print(f"  {f}:{i}: [^{key}]: {line[len(key)+4:][:80]}")
                            break

    return orphans


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    docs_root = Path(__file__).parent.parent / "docs"
    orphans = find_orphan_defs(docs_root, verbose=verbose)

    total = sum(len(o) for _, o in orphans)
    print(f"Orphan footnote defs: {total} in {len(orphans)} files")
    for fpath, keys in orphans:
        print(f"  {fpath}: {sorted(keys)}")

    return 1 if orphans else 0


if __name__ == "__main__":
    sys.exit(main())
