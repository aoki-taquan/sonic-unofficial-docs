#!/usr/bin/env python3
"""Indexer v2: extract HLD metadata (revision date, status, images, age).

Reads `meta/index/hld.json` (read-only), reads each HLD body from
`.cache/sonic-sources/<repo-name>/<path>`, and emits
`meta/index/hld_meta.json` plus `meta/index/_meta_v2_summary.md`.

Does NOT modify the v1 hld.json or any backlog files.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "sonic-sources"
INDEX = ROOT / "meta" / "index"
TODAY = date(2026, 5, 9)

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

STATUS_KEYWORDS = [
    "approved", "final", "reviewed", "in review", "review", "draft",
    "proposal", "initial", "wip", "work in progress",
]


def repo_dir(repo: str) -> Path:
    # repo is "sonic-net/SONiC" -> cache name is the trailing segment
    return CACHE / repo.split("/", 1)[1]


def parse_date_token(s: str) -> date | None:
    s = s.strip().strip(",.;:")
    # ISO YYYY-MM-DD or YYYY/MM/DD
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    # DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


DATE_PATTERNS = [
    # ISO style
    re.compile(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b"),
    # "Mar 15, 2024" / "March 15 2024" / "15 Mar 2024"
    re.compile(r"\b([A-Za-z]{3,9})[.\s]+(\d{1,2})(?:st|nd|rd|th)?[,\s]+(20\d{2})\b"),
    re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?[\s\-]+([A-Za-z]{3,9})[.,\s]+(20\d{2})\b"),
    # "2024-Mar-15"
    re.compile(r"\b(20\d{2})[-/\s]+([A-Za-z]{3,9})[-/\s]+(\d{1,2})\b"),
]


def extract_dates_from_text(text: str) -> list[date]:
    out: list[date] = []
    for line in text.splitlines():
        for pat in DATE_PATTERNS:
            for m in pat.finditer(line):
                g = m.groups()
                d: date | None = None
                try:
                    if g[0].isdigit() and len(g[0]) == 4:
                        # YYYY first
                        if g[1].isdigit():
                            d = date(int(g[0]), int(g[1]), int(g[2]))
                        else:
                            mo = MONTHS.get(g[1].lower()[:9])
                            if mo:
                                d = date(int(g[0]), mo, int(g[2]))
                    elif g[2].isdigit() and len(g[2]) == 4:
                        # YYYY last
                        if g[1].isdigit():
                            # ambiguous DD/MM/YYYY vs MM/DD/YYYY -> assume DD/MM
                            day, mo = int(g[0]), int(g[1])
                            if mo > 12 and day <= 12:
                                day, mo = mo, day
                            if mo > 12:
                                continue
                            d = date(int(g[2]), mo, day)
                        else:
                            mo = MONTHS.get(g[1].lower()[:9])
                            if mo:
                                d = date(int(g[2]), mo, int(g[0]))
                    elif not g[0].isdigit():
                        mo = MONTHS.get(g[0].lower()[:9])
                        if mo:
                            d = date(int(g[2]), mo, int(g[1]))
                except (ValueError, IndexError):
                    d = None
                if d and 2010 <= d.year <= 2026 and d <= TODAY:
                    out.append(d)
    return out


REVISION_HEADER_RE = re.compile(
    r"^#{1,6}\s*(?:revision(?:\s+history|\s+table)?|change\s+log|history)\b",
    re.IGNORECASE,
)
HEADER_RE = re.compile(r"^#{1,6}\s")
TABLE_ROW_RE = re.compile(r"^\s*\|")


def find_revision_section(lines: list[str]) -> tuple[int, int] | None:
    """Return (start, end) line indices for revision section if found."""
    for i, ln in enumerate(lines):
        if REVISION_HEADER_RE.match(ln):
            # find next header
            for j in range(i + 1, min(len(lines), i + 200)):
                if HEADER_RE.match(lines[j]) and not REVISION_HEADER_RE.match(lines[j]):
                    return (i, j)
            return (i, min(len(lines), i + 200))
    return None


def extract_revision(text: str) -> tuple[date | None, int]:
    """Extract latest revision date and revision count from HLD body."""
    lines = text.splitlines()
    sec = find_revision_section(lines)
    if sec is not None:
        start, end = sec
        block = "\n".join(lines[start:end])
        rev_dates = extract_dates_from_text(block)
        # count table data rows (excluding header / separator)
        table_rows = 0
        for ln in lines[start:end]:
            if TABLE_ROW_RE.match(ln):
                # skip separator rows like |---|---|
                if re.match(r"^\s*\|[\s\-:|]+\|\s*$", ln):
                    continue
                table_rows += 1
        # subtract 1 for header row when applicable
        rev_count = max(table_rows - 1, 0) if table_rows >= 2 else (1 if rev_dates else 0)
        if rev_dates:
            return (max(rev_dates), rev_count or 1)
        if rev_count:
            return (None, rev_count)
    # fallback: "Last updated: ..." / first date in first 100 lines
    head = "\n".join(lines[:120])
    m = re.search(r"last\s+updated\s*:?\s*([^\n]+)", head, re.IGNORECASE)
    if m:
        ds = extract_dates_from_text(m.group(1))
        if ds:
            return (max(ds), 1)
    # last-resort: any date in first 200 lines
    early = "\n".join(lines[:200])
    ds = extract_dates_from_text(early)
    if ds:
        return (max(ds), 1)
    return (None, 1)


def extract_status(text: str) -> str:
    lines = text.splitlines()
    # explicit "Status: X" line anywhere
    statuses_found: list[str] = []
    for ln in lines[:300]:
        m = re.search(r"\bstatus\s*[:\-]\s*([A-Za-z][A-Za-z \-]+)", ln, re.IGNORECASE)
        if m:
            val = m.group(1).strip().lower()
            for kw in STATUS_KEYWORDS:
                if val.startswith(kw):
                    statuses_found.append(kw)
                    break
    # scan revision section change descriptions for status keywords
    sec = find_revision_section(lines)
    if sec is not None:
        block = "\n".join(lines[sec[0]:sec[1]]).lower()
        for kw in STATUS_KEYWORDS:
            # take all occurrences in order
            for m in re.finditer(r"\b" + re.escape(kw) + r"\b", block):
                statuses_found.append(kw)
    if statuses_found:
        # last one wins, normalize
        last = statuses_found[-1]
        norm = {
            "approved": "Approved", "final": "Final", "reviewed": "Reviewed",
            "in review": "Reviewed", "review": "Reviewed",
            "draft": "Draft", "proposal": "Proposal", "initial": "Initial",
            "wip": "WIP", "work in progress": "WIP",
        }
        return norm.get(last, last.title())
    return "unknown"


IMG_PATTERNS = [
    re.compile(r"!\[[^\]]*\]\([^)]+\)"),         # markdown image
    re.compile(r"<img\s[^>]*>", re.IGNORECASE),  # html img
    re.compile(r"\b\S+\.(?:png|svg|jpg|jpeg|gif)\b", re.IGNORECASE),
]


def count_images(text: str) -> int:
    seen: set[tuple[int, int]] = set()
    n = 0
    for pat in IMG_PATTERNS:
        for m in pat.finditer(text):
            key = (m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            n += 1
    return n


def estimate_content_size(text: str) -> int:
    # strip fenced code blocks
    t = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # strip indented code blocks (rough)
    t = re.sub(r"(?m)^(?:    |\t).*$", "", t)
    # strip table rows
    t = re.sub(r"(?m)^\s*\|.*\|\s*$", "", t)
    # strip image refs
    for pat in IMG_PATTERNS:
        t = pat.sub("", t)
    # strip HTML tags
    t = re.sub(r"<[^>]+>", "", t)
    # collapse whitespace
    t = re.sub(r"\s+", " ", t)
    return len(t.strip())


def git_last_commit_date(repo_path: Path, file_rel: str) -> date | None:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_path), "log", "-1", "--follow", "--format=%cI", "--", file_rel],
            stderr=subprocess.DEVNULL,
            timeout=15,
        ).decode().strip()
        if out:
            return datetime.fromisoformat(out).date()
    except Exception:
        return None
    return None


def years_between(d: date, ref: date) -> float:
    days = (ref - d).days
    return round(days / 365.25, 1)


def main() -> int:
    hld_index = json.loads((INDEX / "hld.json").read_text())
    out_entries = []
    fallback_used = 0
    for entry in hld_index:
        repo = entry["repo"]
        rel = entry["path"]
        rdir = repo_dir(repo)
        fpath = rdir / rel
        size_bytes = entry.get("size_bytes", 0)
        rev_date: date | None = None
        rev_count = 1
        status = "unknown"
        has_images = False
        image_count = 0
        content_size = 0
        if fpath.is_file():
            try:
                raw = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                raw = ""
            size_bytes = fpath.stat().st_size
            # cap large files at first 10000 lines for sniffing
            lines = raw.splitlines()
            if len(lines) > 10000:
                sniff = "\n".join(lines[:10000])
            else:
                sniff = raw
            rev_date, rev_count = extract_revision(sniff)
            status = extract_status(sniff)
            image_count = count_images(sniff)
            has_images = image_count > 0
            content_size = estimate_content_size(sniff)
        if rev_date is None:
            d = git_last_commit_date(rdir, rel)
            if d is not None:
                rev_date = d
                fallback_used += 1
        age_years = years_between(rev_date, TODAY) if rev_date else None
        out_entries.append({
            "repo": repo,
            "path": rel,
            "revision_date": rev_date.isoformat() if rev_date else None,
            "revision_count": rev_count,
            "status": status,
            "has_images": has_images,
            "image_count": image_count,
            "size_bytes": size_bytes,
            "content_size_bytes": content_size,
            "age_years": age_years,
        })

    payload = {
        "schema_version": 1,
        "indexed_at": datetime.utcnow().isoformat() + "Z",
        "source_index": "meta/index/hld.json",
        "today": TODAY.isoformat(),
        "git_fallback_used": fallback_used,
        "entries": out_entries,
    }
    (INDEX / "hld_meta.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    # summary
    total = len(out_entries)
    status_counts = Counter(e["status"] for e in out_entries)
    age_buckets = Counter()
    for e in out_entries:
        a = e["age_years"]
        if a is None:
            age_buckets["unknown"] += 1
        elif a < 1:
            age_buckets["0-1y"] += 1
        elif a < 3:
            age_buckets["1-3y"] += 1
        elif a < 5:
            age_buckets["3-5y"] += 1
        else:
            age_buckets["5y+"] += 1
    img_pct = round(100 * sum(1 for e in out_entries if e["has_images"]) / total, 1) if total else 0.0
    rev_date_known = sum(1 for e in out_entries if e["revision_date"])
    status_known = sum(1 for e in out_entries if e["status"] != "unknown")

    # candidates: old (>=3y) and Initial / Proposal
    initial_old = [
        e for e in out_entries
        if e["age_years"] is not None and e["age_years"] >= 3
        and e["status"] in {"Initial", "Proposal", "Draft"}
    ]
    initial_old.sort(key=lambda e: -(e["age_years"] or 0))

    # area_hint joined back from v1 index for area-level observation
    v1_by_path = {(e["repo"], e["path"]): e.get("area_hint", "unknown") for e in hld_index}
    area_age_initial: Counter = Counter()
    for e in out_entries:
        if e["status"] in {"Initial", "Proposal", "Draft"} and e["age_years"] and e["age_years"] >= 3:
            area_age_initial[v1_by_path.get((e["repo"], e["path"]), "unknown")] += 1

    lines = []
    lines.append("# HLD Metadata Index v2 — Summary\n")
    lines.append(f"- Total entries: **{total}**")
    lines.append(f"- Revision date extracted: **{rev_date_known}** ({round(100*rev_date_known/total,1)}%)")
    lines.append(f"- Status extracted (not `unknown`): **{status_known}** ({round(100*status_known/total,1)}%)")
    lines.append(f"- HLDs with images: **{img_pct}%**")
    lines.append(f"- git-log fallback used for revision_date: **{fallback_used}**\n")

    lines.append("## Status distribution\n")
    lines.append("| Status | Count |")
    lines.append("|---|---:|")
    for s, c in status_counts.most_common():
        lines.append(f"| {s} | {c} |")
    lines.append("")

    lines.append("## Age distribution\n")
    lines.append("| Bucket | Count |")
    lines.append("|---|---:|")
    for b in ["0-1y", "1-3y", "3-5y", "5y+", "unknown"]:
        lines.append(f"| {b} | {age_buckets.get(b,0)} |")
    lines.append("")

    if area_age_initial:
        lines.append("## Areas with many old + Initial/Proposal/Draft HLDs\n")
        lines.append("| Area | Count |")
        lines.append("|---|---:|")
        for a, c in area_age_initial.most_common():
            lines.append(f"| {a} | {c} |")
        lines.append("")

    if initial_old:
        lines.append("## Top old (>=3y) Initial/Proposal/Draft HLDs (max 20)\n")
        lines.append("| Age (y) | Status | Repo | Path |")
        lines.append("|---:|---|---|---|")
        for e in initial_old[:20]:
            lines.append(f"| {e['age_years']} | {e['status']} | {e['repo']} | `{e['path']}` |")
        lines.append("")

    (INDEX / "_meta_v2_summary.md").write_text("\n".join(lines))

    print(f"wrote {INDEX/'hld_meta.json'} ({total} entries)")
    print(f"wrote {INDEX/'_meta_v2_summary.md'}")
    print(f"  rev_date_known={rev_date_known} status_known={status_known} img_pct={img_pct}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
