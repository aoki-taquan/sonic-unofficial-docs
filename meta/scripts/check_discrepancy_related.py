#!/usr/bin/env python3
"""Lint helper: report `verification: discrepancy-found` pages whose
frontmatter `related.yang` list is empty.

Rationale: HLD-derived discrepancy pages typically reference at least one
YANG module in the body. Leaving `related.yang` empty hides those back-refs
from the related-pages sidebar and lowers axis 4 (relatedness) in the
quality audit (see meta/quality-audit-27.md improvement #2).

This script is **informational only** — it prints a report to stdout and
exits 0 even when violations are found, unless `--strict` is passed.
That keeps it suitable for `|| true` style CI integration alongside other
informational linters in `.github/workflows/ci.yml`.

Usage:
    meta/scripts/check_discrepancy_related.py [--root .] [--strict]
                                               [--report PATH]

Skip semantics:
- Pages whose `related._no_related: true` are excluded (explicit opt-out
  from all related-pages back-refs).
- Pages whose `related._no_yang: true` are excluded (narrower opt-out:
  the feature has no YANG model by design — e.g. HLD-only proposals
  that pre-date YANG modelling, platform-only behaviour with no
  CONFIG_DB schema, etc.).
- Only pages whose top-level frontmatter contains
  `verification: discrepancy-found` are scanned.

Exit codes:
- 0: always, unless `--strict` and at least one violation exists.
- 1: `--strict` and one or more violations exist.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def split_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None


def is_opted_out(fm: dict) -> bool:
    rel = fm.get("related") or {}
    if not isinstance(rel, dict):
        return False
    return (
        rel.get("_no_related") is True
        or rel.get("_no_related_yang") is True
        or rel.get("_no_yang") is True
    )


def yang_is_empty(fm: dict) -> bool:
    rel = fm.get("related")
    if not isinstance(rel, dict):
        return True
    v = rel.get("yang") or []
    return not (isinstance(v, list) and len(v) > 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root")
    ap.add_argument(
        "--targets",
        default="docs",
        help="comma-separated directories to scan (default: docs)",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when at least one discrepancy page has empty related.yang",
    )
    ap.add_argument(
        "--report",
        default=None,
        help="write a markdown report to this path",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    target_dirs = [d.strip() for d in args.targets.split(",") if d.strip()]

    scanned = 0
    discrepancy_total = 0
    violations: list[Path] = []
    opted: list[Path] = []

    for d in target_dirs:
        full = root / d
        if not full.is_dir():
            continue
        for p in sorted(full.rglob("*.md")):
            if p.name == "index.md":
                continue
            try:
                t = p.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = split_frontmatter(t)
            if fm is None:
                continue
            scanned += 1
            if fm.get("verification") != "discrepancy-found":
                continue
            discrepancy_total += 1
            if is_opted_out(fm):
                opted.append(p)
                continue
            if yang_is_empty(fm):
                violations.append(p)

    print(
        f"scanned {scanned} pages, "
        f"{discrepancy_total} discrepancy-found, "
        f"{len(violations)} have empty related.yang, "
        f"{len(opted)} opted out (_no_related / _no_yang)",
        file=sys.stderr,
    )

    for p in violations:
        print(p.relative_to(root))

    if args.report:
        out: list[str] = []
        out.append("# `verification: discrepancy-found` pages with empty `related.yang`")
        out.append("")
        out.append("Informational lint — discrepancy-found pages typically reference")
        out.append("YANG modules in the body. Leaving `related.yang` empty hides those")
        out.append("back-refs from the related-pages sidebar.")
        out.append("")
        out.append(f"- scanned: {scanned}")
        out.append(f"- discrepancy-found total: {discrepancy_total}")
        out.append(f"- empty `related.yang`: {len(violations)}")
        out.append(f"- opted out (`_no_related` / `_no_yang`): {len(opted)}")
        out.append("")
        out.append("## Violations")
        out.append("")
        for p in violations:
            out.append(f"- `{p.relative_to(root)}`")
        out.append("")
        out.append("## Opted-out")
        out.append("")
        for p in opted:
            out.append(f"- `{p.relative_to(root)}`")
        out.append("")
        rp = Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text("\n".join(out), encoding="utf-8")
        print(f"wrote report to {rp}", file=sys.stderr)

    if args.strict and violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
