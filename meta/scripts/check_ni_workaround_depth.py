#!/usr/bin/env python3
"""Lint that checks whether ``monitor: not_implemented`` pages document
sufficiently deep workarounds / alternatives.

A page tagged ``monitor: not_implemented`` describes a feature that is NOT
present in current master. For such pages, readers need actionable guidance
on how to work around the missing feature. This linter requires that the
body contains, in the vicinity of "代替手段" / "回避策" / "workaround" /
"代替策" / "代替案" markers:

* At least 2 distinct command-like tokens (fenced code blocks, inline
  ``code`` runs, or sentences containing ``$``/CLI hints), AND
* At least 2 bullet/numbered list items OR enumerated steps.

Pages that fail both thresholds are flagged as "shallow workaround".

Usage::

    python3 meta/scripts/check_ni_workaround_depth.py            # report
    python3 meta/scripts/check_ni_workaround_depth.py --check    # informational (exit 0)
    python3 meta/scripts/check_ni_workaround_depth.py --report   # markdown table
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)

# Section / paragraph triggers that introduce an alternative or workaround.
WORKAROUND_MARKERS = [
    r"代替手段",
    r"代替策",
    r"代替案",
    r"代替機能",
    r"回避策",
    r"ワークアラウンド",
    r"workaround",
    r"alternative",
]
MARKER_RE = re.compile("|".join(WORKAROUND_MARKERS), re.IGNORECASE)

FENCED_CODE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
BULLET_RE = re.compile(r"^\s{0,8}(?:[-*+]|\d+\.)\s+\S", re.MULTILINE)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm, text[m.end():]


def extract_workaround_regions(body: str) -> list[str]:
    """Return body regions that follow a workaround marker.

    Each region spans from a marker hit to the next blank-line gap of length
    >= 2, or to the next top-level header, whichever comes first. We keep the
    region wide enough to include code blocks, bullets and tip/admonition
    bodies that follow the marker.
    """
    regions: list[str] = []
    lines = body.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        if MARKER_RE.search(lines[i]):
            start = i
            blank_streak = 0
            j = i + 1
            while j < n:
                stripped = lines[j].strip()
                if stripped.startswith("## ") or stripped.startswith("# "):
                    break
                if not stripped:
                    blank_streak += 1
                    if blank_streak >= 2:
                        break
                else:
                    blank_streak = 0
                j += 1
            regions.append("\n".join(lines[start:j]))
            i = j
        else:
            i += 1
    return regions


def count_commands(region: str) -> int:
    """Count distinct command-like tokens (fenced + inline + $-prefixed)."""
    cmds: set[str] = set()
    for m in FENCED_CODE_RE.finditer(region):
        # Each non-empty line inside a fenced block counts as 1 command.
        body = m.group(0)
        body = re.sub(r"^```.*\n", "", body, count=1)
        body = re.sub(r"\n```$", "", body)
        for line in body.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            cmds.add(s)
    for m in INLINE_CODE_RE.finditer(region):
        token = m.group(0).strip("`").strip()
        # Keep only tokens that look command-ish: contain a space or CLI hint.
        if not token:
            continue
        if (
            " " in token
            or token.startswith("$")
            or "/" in token
            or "-" in token and token.lower() != token.upper()
        ):
            # filter pure paths like ../foo.md and identifiers
            if re.search(r"[A-Za-z]", token) and not token.endswith(".md"):
                cmds.add(token)
    return len(cmds)


def count_steps(region: str) -> int:
    """Count bullet / numbered list items inside the region."""
    # Drop fenced code blocks so bullets inside them are not double-counted.
    clean = FENCED_CODE_RE.sub("", region)
    return len(BULLET_RE.findall(clean))


def evaluate(body: str) -> tuple[bool, int, int]:
    regions = extract_workaround_regions(body)
    if not regions:
        return False, 0, 0
    total_cmds = sum(count_commands(r) for r in regions)
    total_steps = sum(count_steps(r) for r in regions)
    ok = total_cmds >= 2 and total_steps >= 2
    return ok, total_cmds, total_steps


def collect() -> list[dict[str, object]]:
    suspects: list[dict[str, object]] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(md.relative_to(REPO_ROOT))
        text = md.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        if fm.get("monitor") != "not_implemented":
            continue
        ok, cmds, steps = evaluate(body)
        if ok:
            continue
        suspects.append(
            {
                "path": rel,
                "commands": cmds,
                "steps": steps,
            }
        )
    return suspects


def render_report(suspects: list[dict[str, object]]) -> str:
    if not suspects:
        return "No shallow-workaround pages found.\n"
    lines = [
        "# not_implemented workaround depth report\n",
        f"Total shallow pages: {len(suspects)}\n",
        "Threshold: >= 2 commands AND >= 2 steps inside 代替手段 / 回避策 / workaround regions.\n",
        "| Path | commands | steps |",
        "|---|---|---|",
    ]
    for s in suspects:
        lines.append(f"| `{s['path']}` | {s['commands']} | {s['steps']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="informational mode (count to stderr, exit 0)")
    ap.add_argument("--report", action="store_true",
                    help="print markdown table of suspects to stdout")
    args = ap.parse_args()

    suspects = collect()

    if args.report:
        print(render_report(suspects))
    elif args.check:
        print(f"ni-workaround-depth suspects: {len(suspects)}", file=sys.stderr)
        for s in suspects[:30]:
            print(f"  {s['path']} commands={s['commands']} steps={s['steps']}",
                  file=sys.stderr)
    else:
        if not suspects:
            print("No shallow-workaround pages found.")
            return 0
        print(f"Found {len(suspects)} shallow-workaround page(s):")
        for s in suspects:
            print(f"  {s['path']} commands={s['commands']} steps={s['steps']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
