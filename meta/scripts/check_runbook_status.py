#!/usr/bin/env python3
"""Check that docs/reference/runbooks/*.md pages do not regress to ``hld-only``.

Runbook は実機 / コードでの裏取りが前提のページ群で、
``verification`` は ``code-verified`` / ``runbook-verified`` / ``discrepancy-found``
のいずれかであるべき。``hld-only`` や ``issue-confirmed`` は不適。

Usage:
    python3 meta/scripts/check_runbook_status.py            # 一覧表示
    python3 meta/scripts/check_runbook_status.py --check    # CI gate (>0 で exit 1)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_DIR = REPO_ROOT / "docs" / "reference" / "runbooks"

VALID_VERIFICATIONS = {"code-verified", "runbook-verified", "discrepancy-found"}
INVALID_VERIFICATIONS = {"hld-only", "issue-confirmed"}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# index ページなど runbook 本体ではないものを除外
SKIP_FILES = {"index.md"}


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        # ネストキー (related: のサブ要素など) は無視するため、
        # インデントされた行はスキップ
        if key.startswith(" ") or key.startswith("\t") or key.startswith("-"):
            continue
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def collect_runbooks() -> list[Path]:
    if not RUNBOOK_DIR.exists():
        return []
    return sorted(p for p in RUNBOOK_DIR.glob("*.md") if p.name not in SKIP_FILES)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI モード: hld-only / issue-confirmed が 1 件でもあれば exit 1",
    )
    args = parser.parse_args()

    runbooks = collect_runbooks()
    invalid: list[tuple[Path, str]] = []
    missing: list[Path] = []

    for path in runbooks:
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        verification = fm.get("verification", "")
        if not verification:
            missing.append(path)
            continue
        if verification in INVALID_VERIFICATIONS:
            invalid.append((path, verification))
            continue
        if verification not in VALID_VERIFICATIONS:
            invalid.append((path, verification))

    rel = lambda p: p.relative_to(REPO_ROOT).as_posix()

    if invalid:
        print(
            f"[check_runbook_status] Found {len(invalid)} runbook(s) with invalid verification:",
            file=sys.stderr,
        )
        for path, ver in invalid:
            print(f"  - {rel(path)}: verification={ver!r}", file=sys.stderr)
        print(
            "  Allowed: " + ", ".join(sorted(VALID_VERIFICATIONS)),
            file=sys.stderr,
        )

    if missing:
        print(
            f"[check_runbook_status] {len(missing)} runbook(s) without verification field:",
            file=sys.stderr,
        )
        for path in missing:
            print(f"  - {rel(path)}", file=sys.stderr)

    total_bad = len(invalid) + len(missing)
    if not total_bad:
        print(
            f"[check_runbook_status] OK: {len(runbooks)} runbook(s) all have valid verification.",
        )
        return 0

    if args.check:
        print(
            f"[check_runbook_status] FAIL: {total_bad} runbook(s) need fixing.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
