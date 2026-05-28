#!/usr/bin/env python3
"""One-shot: suppress noisy auto-injected `related.config_db` / `related.yang`
on the cross-cutting / orientation topics chapters.

These chapters (01-overview, 20-swss-sai-redis, 21-lab-vs-developer,
22-reference-index) are reading / navigation pages, not feature reference. The
`backfill_related.py` slug/title token prefix-matcher injected a grab-bag of
unrelated CDB tables and YANG modules (DASH_ENI_TABLE, PFC_WD, BGP_* dumps on
pages with no thematic tie). That feeds spurious overlap into
`gen_next_reads.py` chapter-signature ranking and misleads readers.

Fix: clear `related.config_db` and `related.yang`, and set the schema-sanctioned
narrower opt-out markers `_no_related_config_db` / `_no_related_yang` so the
back-fill never repopulates them and `frontmatter_lint.py` stays happy. The
`related.cli` list is kept (navigationally useful, generally on-theme) unless
it is already empty.

The genuine reference index pages (cli-index / config-db-index / yang-index)
and pages already opted out via the older `_no_related_cli` / `_no_related_cdb`
markers are excluded -- their CDB/YANG references are on-theme.

Not part of CI; run once.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CHAPTERS = [
    "docs/topics/01-overview",
    "docs/topics/20-swss-sai-redis",
    "docs/topics/21-lab-vs-developer",
    "docs/topics/22-reference-index",
]
# Genuine reference-index pages whose CDB/YANG lists are on-theme, and pages
# already opted out via the older markers -- leave these untouched.
EXCLUDE = {
    "22-reference-index/cli-index.md",
    "22-reference-index/config-db-index.md",
    "22-reference-index/yang-index.md",
    "22-reference-index/operations.md",
    "22-reference-index/setup.md",
}

FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def main() -> None:
    changed = 0
    for chap in CHAPTERS:
        d = ROOT / chap
        for p in sorted(d.glob("*.md")):
            if p.name == "index.md":
                continue
            rel_id = f"{Path(chap).name}/{p.name}"
            if rel_id in EXCLUDE:
                continue
            text = p.read_text(encoding="utf-8")
            m = FM_RE.match(text)
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            rel = fm.get("related")
            if not isinstance(rel, dict):
                continue
            body = text[m.end():]

            before = (rel.get("config_db"), rel.get("yang"),
                      rel.get("_no_related_config_db"),
                      rel.get("_no_related_yang"))

            rel["config_db"] = []
            rel["yang"] = []
            rel["_no_related_config_db"] = True
            rel["_no_related_yang"] = True
            rel.pop("_no_related", None)

            after = (rel["config_db"], rel["yang"],
                     rel["_no_related_config_db"], rel["_no_related_yang"])
            if before == after:
                continue

            fm["related"] = rel
            new_fm = yaml.safe_dump(
                fm, allow_unicode=True, sort_keys=False,
                default_flow_style=False,
            )
            p.write_text("---\n" + new_fm + "---\n" + body, encoding="utf-8")
            changed += 1
            print(f"[UPDATE] {p.relative_to(ROOT)}")
    print(f"\n{changed} pages updated")


if __name__ == "__main__":
    main()
