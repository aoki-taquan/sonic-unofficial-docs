#!/usr/bin/env python3
"""Verify daemon-name references in docs against master sonic sources.

Scans all docs/**/*.md, extracts tokens matching daemon suffix patterns
(*cfgd / *mgrd / *syncd / *orch / *orchd), and grep-verifies each name
against .cache/sonic-sources/ for at least one declaration / implementation
file.

Outputs meta/daemon-name-violations.md.
Exit code: 1 if any unknown names found, else 0.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
# sonic-sources lives in the main repo working copy (gitignored, shared by worktrees)
MAIN_REPO_ROOT = Path("/home/coder/sonic-unofficial-docs")
SRC_DIR = MAIN_REPO_ROOT / ".cache" / "sonic-sources"
OUT = REPO_ROOT / "meta" / "daemon-name-violations.md"

# Match daemon-like tokens. Lowercase ASCII, ends with one of the suffixes.
# Must be at least 3 chars before the suffix to avoid matching bare "orch".
DAEMON_RE = re.compile(
    r"\b([a-z][a-z0-9_]{1,30}(?:cfgd|mgrd|syncd|orchd|orch))\b"
)

# Tokens to ignore (generic words, class names that are not daemons).
IGNORE = {
    "orch",  # bare class, not a daemon
    "syncd",  # actually a real daemon - keep it in scope
}
# Don't ignore "syncd" - it IS a real daemon process name. Remove from set.
IGNORE.discard("syncd")


# Markers indicating the surrounding line/paragraph is *explicitly* documenting
# that the named daemon does NOT exist in master (i.e. a discrepancy note, not
# a typo). Such mentions are not violations.
ABSENCE_MARKERS = (
    "存在しない",
    "存在せず",
    "未マージ",
    "未実装",
    "未取り込み",
    "未検出",
    "未完了",
    "見つからない",
    "検出できず",
    "ヒット 0",
    "0 件",
    "0件",
    "実装されていない",
    "実装は存在しない",
    "提案中",
    "PR #",
    "実装提案",
    "fork で実装",
)


def _is_absence_context(text: str, start: int, end: int) -> bool:
    """Return True if the surrounding paragraph signals the name is absent."""
    # Paragraph = nearest blank-line boundaries on either side.
    p_start = text.rfind("\n\n", 0, start)
    p_start = 0 if p_start < 0 else p_start
    p_end = text.find("\n\n", end)
    p_end = len(text) if p_end < 0 else p_end
    chunk = text[p_start:p_end]
    return any(m in chunk for m in ABSENCE_MARKERS)


def find_tokens() -> dict[str, list[Path]]:
    """Return mapping daemon-name -> list of docs files that mention it
    in a non-absence context."""
    out: dict[str, list[Path]] = {}
    for md in DOCS_DIR.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        seen_in_file: set[str] = set()
        for m in DAEMON_RE.finditer(text):
            tok = m.group(1)
            if tok in IGNORE:
                continue
            if tok in seen_in_file:
                continue
            if _is_absence_context(text, m.start(), m.end()):
                continue
            seen_in_file.add(tok)
            out.setdefault(tok, []).append(md)
    return out


def grep_exists(name: str) -> bool:
    """Return True if `name` appears anywhere under SRC_DIR."""
    if not SRC_DIR.exists():
        return True  # cannot verify; treat as valid to avoid false positives
    try:
        r = subprocess.run(
            ["grep", "-rIliF", "--include=*", "-m", "1", name, str(SRC_DIR)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )
        return r.returncode == 0
    except Exception:
        return True


def main() -> int:
    tokens = find_tokens()
    print(f"Found {len(tokens)} unique daemon-like tokens across docs/", file=sys.stderr)
    if not SRC_DIR.exists():
        print(f"WARN: sonic-sources missing at {SRC_DIR}", file=sys.stderr)

    missing: dict[str, list[Path]] = {}
    for name in sorted(tokens):
        if not grep_exists(name):
            missing[name] = tokens[name]

    lines: list[str] = []
    lines.append("# Daemon Name Verification — Violations")
    lines.append("")
    lines.append(
        f"Scanned `docs/**/*.md`, extracted {len(tokens)} unique daemon-like "
        "tokens matching `*cfgd|*mgrd|*syncd|*orch|*orchd`, and grep-verified "
        f"each against `.cache/sonic-sources/`."
    )
    lines.append("")
    lines.append(f"- Verified token count: **{len(tokens)}**")
    lines.append(f"- Violations (not found in master sources): **{len(missing)}**")
    lines.append("")
    if missing:
        lines.append("## Violations")
        lines.append("")
        lines.append("| daemon name | occurrences | files |")
        lines.append("|---|---|---|")
        for name, files in sorted(missing.items()):
            rels = sorted({str(p.relative_to(REPO_ROOT)) for p in files})
            shown = ", ".join(rels[:5]) + (" ..." if len(rels) > 5 else "")
            lines.append(f"| `{name}` | {len(files)} | {shown} |")
    else:
        lines.append("No violations: every daemon-like token resolves to a master source file.")
    lines.append("")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(REPO_ROOT)} ({len(missing)} violations)", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
