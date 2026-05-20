#!/usr/bin/env python3
"""Find docs pages whose frontmatter `related.{cli,config_db,yang}` is fully
empty (all three lists missing or `[]`).

Audit lever for the 6-axis quality score, axis 4 (relatedness). Use the
output to either:

 1. Re-run `backfill_related.py --mode aggressive` to back-fill heuristically.
 2. Mark the page with `related: { _no_related: true }` to opt out (used
    when no genuine reference page applies).

Pages whose `related` dict contains the marker key `_no_related: true` are
treated as **explicitly opted out** and excluded from the empty report.

Usage:
    meta/scripts/find_empty_related.py [--root .] [--report PATH]
                                       [--targets DIR[,DIR...]]

Default scan covers every `docs/**/*.md` except `index.md`.

Exits 0 always; this is a report-only tool (not a CI gate).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
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


def is_empty_related(fm: dict) -> bool:
    rel = fm.get("related")
    if not isinstance(rel, dict):
        # No related dict at all -> empty.
        return True
    if rel.get("_no_related") is True:
        # Explicit opt-out marker.
        return False
    for key in ("cli", "config_db", "yang"):
        v = rel.get(key) or []
        if isinstance(v, list) and v:
            return False
    return True


def is_opted_out(fm: dict) -> bool:
    rel = fm.get("related") or {}
    return isinstance(rel, dict) and rel.get("_no_related") is True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root")
    ap.add_argument(
        "--targets",
        default="docs",
        help="comma-separated directories to scan (default: docs)",
    )
    ap.add_argument(
        "--report",
        default=None,
        help="write a markdown report to this path",
    )
    ap.add_argument(
        "--exclude",
        default="docs/reference/cli,docs/reference/config-db,docs/reference/yang",
        help=(
            "comma-separated directories to exclude (reference triangle "
            "pages legitimately have empty related)"
        ),
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    target_dirs = [d.strip() for d in args.targets.split(",") if d.strip()]
    exclude_dirs = [
        (root / d.strip()).resolve()
        for d in args.exclude.split(",")
        if d.strip()
    ]

    def is_excluded(p: Path) -> bool:
        try:
            rp = p.resolve()
        except OSError:
            return False
        for ed in exclude_dirs:
            try:
                rp.relative_to(ed)
                return True
            except ValueError:
                continue
        return False

    empty: list[Path] = []
    opted: list[Path] = []
    total = 0

    by_area: Counter = Counter()
    for d in target_dirs:
        full = root / d
        if not full.is_dir():
            continue
        for p in sorted(full.rglob("*.md")):
            if p.name == "index.md":
                continue
            if is_excluded(p):
                continue
            try:
                t = p.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = split_frontmatter(t)
            if fm is None:
                continue
            total += 1
            if is_opted_out(fm):
                opted.append(p)
                continue
            if is_empty_related(fm):
                empty.append(p)
                rel_path = p.relative_to(root)
                area = (
                    rel_path.parts[1]
                    if len(rel_path.parts) > 1 else rel_path.parts[0]
                )
                by_area[area] += 1

    print(
        f"scanned {total} pages, "
        f"{len(empty)} have fully-empty related, "
        f"{len(opted)} are explicitly opted out (_no_related)",
        file=sys.stderr,
    )

    if args.report:
        out_lines: list[str] = []
        out_lines.append("# Empty `related` report")
        out_lines.append("")
        out_lines.append(
            "Pages whose frontmatter `related.{cli,config_db,yang}` is "
            "fully empty (all three lists missing or `[]`)."
        )
        out_lines.append("")
        out_lines.append("- scanned: " + str(total))
        out_lines.append("- empty: " + str(len(empty)))
        out_lines.append("- opted-out (`_no_related: true`): " + str(len(opted)))
        out_lines.append(
            "- excluded dirs: " + ", ".join(
                str(Path(d.strip()))
                for d in args.exclude.split(",") if d.strip()
            )
        )
        out_lines.append("")
        out_lines.append("## By area")
        out_lines.append("")
        for area, cnt in by_area.most_common():
            out_lines.append(f"- `{area}`: {cnt}")
        out_lines.append("")
        out_lines.append("## Empty pages")
        out_lines.append("")
        for p in empty:
            out_lines.append(f"- `{p.relative_to(root)}`")
        out_lines.append("")
        out_lines.append("## Opted-out pages")
        out_lines.append("")
        for p in opted:
            out_lines.append(f"- `{p.relative_to(root)}`")
        out_lines.append("")
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(out_lines), encoding="utf-8")
        print(f"wrote report to {report_path}", file=sys.stderr)
    else:
        for p in empty:
            print(p.relative_to(root))

    return 0


if __name__ == "__main__":
    sys.exit(main())
