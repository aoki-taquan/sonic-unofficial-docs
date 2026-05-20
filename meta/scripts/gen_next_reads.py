#!/usr/bin/env python3
"""Generate '次に読むべき記事' section for 22 topic chapter-index pages.

For each docs/topics/NN-slug/index.md the script computes three lists:

  1. 読む順 (child pages): concept / setup / operations / internals / advanced
     (also architecture if present). Order is fixed.
  2. 関連する HLD: 5-7 pages from mapped area directories, ranked by
     overlap of frontmatter `keywords` between the chapter and candidate.
  3. 関連 Runbook: 3-5 pages from docs/reference/runbooks/, ranked by
     keyword overlap (chapter keywords vs runbook title + keywords +
     related cli/config_db tokens).

The generated block is inserted (or replaced) just before the
`<!-- xref-related-chapters -->` marker, surrounded by:

    <!-- next-reads -->
    ...
    <!-- /next-reads -->

The chapter→area mapping is explicit (declared in CHAPTER_MAP below) so
runs are deterministic. `--check` returns exit code 1 when any chapter
would change (drift mode for CI).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
TOPICS_DIR = DOCS / "topics"
RUNBOOK_DIR = DOCS / "reference" / "runbooks"

BEGIN = "<!-- next-reads -->"
END = "<!-- /next-reads -->"
ANCHOR = "<!-- xref-related-chapters -->"

# Order of preferred child pages and human-readable label.
CHILD_ORDER = [
    ("concept.md", "概要"),
    ("architecture.md", "アーキテクチャ"),
    ("setup.md", "設定"),
    ("configuration.md", "設定"),
    ("operations.md", "運用"),
    ("internals.md", "内部実装"),
    ("advanced.md", "発展トピック"),
]

# Chapter -> list of area subdirs to scan for related HLDs.
CHAPTER_MAP: dict[str, dict[str, list[str]]] = {
    "01-overview": {"areas": ["architecture", "management", "system"]},
    "02-bgp": {"areas": ["routing"]},
    "03-vxlan-evpn": {"areas": ["overlay"]},
    "04-vrf-ecmp": {"areas": ["routing", "overlay"]},
    "05-dual-tor": {"areas": ["overlay", "switching"]},
    "06-l2-vlan-lag": {"areas": ["switching"]},
    "07-acl-copp-mirror": {"areas": ["acl-qos"]},
    "08-qos-buffer": {"areas": ["acl-qos"]},
    "09-telemetry-snmp": {"areas": ["management", "system"]},
    "10-gnmi-openconfig": {"areas": ["management"]},
    "11-reboot": {"areas": ["system", "management"]},
    "12-multi-asic-voq": {"areas": ["architecture", "platform"]},
    "13-dash-smartswitch": {"areas": ["overlay", "platform"]},
    "14-platform-port-optics": {"areas": ["platform"]},
    "15-security-aaa": {"areas": ["management", "system"]},
    "16-nat-dhcp-dns": {"areas": ["switching", "system"]},
    "17-srv6-mpls": {"areas": ["routing", "overlay"]},
    "18-p4-pins": {"areas": ["internals", "architecture"]},
    "19-build-packaging": {"areas": ["system", "architecture"]},
    "20-swss-sai-redis": {"areas": ["internals", "architecture"]},
    "21-lab-vs-developer": {"areas": ["system", "architecture", "guides"]},
    "22-reference-index": {"areas": ["management", "system", "architecture"]},
}


def split_frontmatter(text: str):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return yaml.safe_load(text[4:end]), text[end + 5 :]


def load_fm(p: Path) -> dict:
    try:
        fm, _ = split_frontmatter(p.read_text(encoding="utf-8"))
        return fm or {}
    except Exception:
        return {}


def normalize_tokens(values) -> set[str]:
    out: set[str] = set()
    if not values:
        return out
    if isinstance(values, dict):
        for v in values.values():
            out |= normalize_tokens(v)
        return out
    if isinstance(values, str):
        values = [values]
    for s in values:
        s = str(s).lower()
        # split on common separators so multi-word keywords match by component
        for tok in re.split(r"[\s/_\-,:]+", s):
            tok = tok.strip()
            if len(tok) >= 3:
                out.add(tok)
    return out


def chapter_signature(fm: dict, slug: str) -> set[str]:
    sig: set[str] = set()
    sig |= normalize_tokens(fm.get("keywords"))
    sig |= normalize_tokens(fm.get("title"))
    rel = fm.get("related") or {}
    if isinstance(rel, dict):
        sig |= normalize_tokens(rel.get("cli"))
        sig |= normalize_tokens(rel.get("config_db"))
        sig |= normalize_tokens(rel.get("yang"))
    # slug tokens too
    sig |= normalize_tokens(slug.split("-", 1)[1] if "-" in slug else slug)
    # remove very generic stopwords
    sig -= {"sonic", "show", "config", "the", "and", "for"}
    return sig


def candidate_signature(fm: dict, path: Path) -> set[str]:
    sig: set[str] = set()
    sig |= normalize_tokens(fm.get("keywords"))
    sig |= normalize_tokens(fm.get("title"))
    rel = fm.get("related") or {}
    if isinstance(rel, dict):
        sig |= normalize_tokens(rel.get("cli"))
        sig |= normalize_tokens(rel.get("config_db"))
        sig |= normalize_tokens(rel.get("yang"))
    sig |= normalize_tokens(path.stem)
    return sig


def rank_by_overlap(chapter_sig: set[str], candidates: list[tuple[Path, dict]]) -> list[tuple[Path, dict, int]]:
    scored = []
    for p, fm in candidates:
        cs = candidate_signature(fm, p)
        score = len(chapter_sig & cs)
        if score > 0:
            scored.append((p, fm, score))
    scored.sort(key=lambda t: (-t[2], t[0].name))
    return scored


def collect_area_pages(areas: list[str]) -> list[tuple[Path, dict]]:
    out = []
    for a in areas:
        d = DOCS / a
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            if p.name == "index.md":
                continue
            fm = load_fm(p)
            if not fm:
                continue
            out.append((p, fm))
    return out


def collect_runbooks() -> list[tuple[Path, dict]]:
    if not RUNBOOK_DIR.is_dir():
        return []
    out = []
    for p in sorted(RUNBOOK_DIR.glob("*.md")):
        if p.name == "index.md":
            continue
        fm = load_fm(p)
        if not fm:
            continue
        out.append((p, fm))
    return out


def rel_link(target: Path, base: Path) -> str:
    # compute relative path from base (the chapter index.md) to target
    rel = Path("../..") / target.relative_to(DOCS)
    return str(rel).replace("\\", "/")


def build_block(chapter_path: Path, slug: str, body: str) -> tuple[str, dict]:
    chap_dir = chapter_path.parent
    chap_fm = load_fm(chapter_path)
    chap_sig = chapter_signature(chap_fm, slug)

    # 1) children
    children = []
    seen = set()
    for fname, label in CHILD_ORDER:
        cp = chap_dir / fname
        if cp.exists() and cp.name not in seen:
            seen.add(cp.name)
            cfm = load_fm(cp)
            title = cfm.get("title") or cp.stem
            children.append((cp.name, label, title))

    # 2) related HLDs
    mapping = CHAPTER_MAP.get(slug, {})
    areas = mapping.get("areas", [])
    area_pages = collect_area_pages(areas)
    ranked = rank_by_overlap(chap_sig, area_pages)
    hld_pick = ranked[:7]
    if len(hld_pick) < 5:
        # pad with highest-by-name from same areas to reach 5 if available
        existing = {p for p, _, _ in hld_pick}
        for p, fm in area_pages:
            if p in existing:
                continue
            hld_pick.append((p, fm, 0))
            if len(hld_pick) >= 5:
                break

    # 3) runbooks
    runbooks = collect_runbooks()
    rb_ranked = rank_by_overlap(chap_sig, runbooks)
    rb_pick = rb_ranked[:5]
    if len(rb_pick) < 3:
        rb_pick = rb_ranked[: min(3, len(rb_ranked))]

    # Render
    lines = []
    lines.append(BEGIN)
    lines.append("## 次に読むべき記事")
    lines.append("")
    if children:
        lines.append("**この章を読み進める順**")
        lines.append("")
        for fname, label, title in children:
            if str(title).strip() == label:
                lines.append(f"- [{label}]({fname})")
            else:
                lines.append(f"- [{label}: {title}]({fname})")
        lines.append("")
    if hld_pick:
        lines.append(f"**関連する HLD {len(hld_pick)} 件**")
        lines.append("")
        for p, fm, _ in hld_pick:
            t = fm.get("title") or p.stem
            lines.append(f"- [{t}]({rel_link(p, chapter_path)})")
        lines.append("")
    if rb_pick:
        lines.append(f"**関連トラブルシュート {len(rb_pick)} 件**")
        lines.append("")
        for p, fm, _ in rb_pick:
            t = fm.get("title") or p.stem
            lines.append(f"- [{t}]({rel_link(p, chapter_path)})")
        lines.append("")
    lines.append(END)
    block = "\n".join(lines).rstrip() + "\n"

    stats = {
        "children": len(children),
        "hld": len(hld_pick),
        "runbooks": len(rb_pick),
    }
    return block, stats


def upsert_block(body: str, block: str) -> str:
    # Remove any existing block between BEGIN/END
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)
    body_clean = pattern.sub("", body)

    # Insert before the xref anchor; if anchor missing, append before
    # glossary-links marker; else append at end.
    if ANCHOR in body_clean:
        insert_at = body_clean.index(ANCHOR)
        # ensure there is a blank line before
        before = body_clean[:insert_at].rstrip() + "\n\n"
        after = body_clean[insert_at:]
        return before + block + "\n" + after
    return body_clean.rstrip() + "\n\n" + block


def process_chapter(idx: Path, check_only: bool) -> tuple[bool, dict]:
    slug = idx.parent.name
    text = idx.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        return False, {"slug": slug, "error": "no-frontmatter"}

    block, stats = build_block(idx, slug, body)
    new_body = upsert_block(body, block)
    if new_body == body:
        return False, {"slug": slug, "changed": False, **stats}

    if check_only:
        return True, {"slug": slug, "changed": True, **stats}

    # write back
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=4096)
    idx.write_text("---\n" + fm_text + "---\n" + new_body, encoding="utf-8")
    return True, {"slug": slug, "changed": True, **stats}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if any chapter would change")
    args = ap.parse_args()

    if not TOPICS_DIR.is_dir():
        print(f"topics dir not found: {TOPICS_DIR}", file=sys.stderr)
        return 2

    indexes = sorted(p for p in TOPICS_DIR.glob("*/index.md"))
    drift = 0
    total = 0
    for idx in indexes:
        changed, stats = process_chapter(idx, args.check)
        total += 1
        if changed:
            drift += 1
        print(
            f"{'DRIFT' if changed and args.check else ('WROTE' if changed else 'OK   ')} "
            f"{stats.get('slug')}: children={stats.get('children', 0)} "
            f"hld={stats.get('hld', 0)} runbooks={stats.get('runbooks', 0)}"
        )
    print(f"---\nProcessed {total} chapters, {drift} changed")
    if args.check and drift:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
