#!/usr/bin/env python3
"""Generate backlog JSON entries from hld.json index."""
import json
import os
import re
from pathlib import Path

ROOT = Path("/home/coder/sonic-unofficial-docs")
INDEX = ROOT / "meta/index/hld.json"
BACKLOG_DIR = ROOT / "meta/backlog"
SOURCES_ROOT = ROOT / ".cache/sonic-sources"


def slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:80] or "untitled"


def extract_questions(repo_path: Path) -> list[str]:
    """Light scan of HLD body to extract section headings as reader questions."""
    if not repo_path.exists():
        return []
    try:
        text = repo_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    headings = re.findall(r"^##+\s+(.+?)\s*$", text, re.MULTILINE)
    # Pick interesting ones
    interesting = []
    for h in headings:
        hl = h.lower()
        if any(k in hl for k in ("overview", "design", "requirement", "configur", "use case", "behavior", "scenario", "introduction", "scope")):
            interesting.append(h.strip("#").strip())
        if len(interesting) >= 3:
            break
    return [f"What is described in '{h}'?" for h in interesting]


def main():
    entries = json.loads(INDEX.read_text())
    by_area = {}
    for e in entries:
        area = e.get("area_hint") or "unknown"
        if area == "unknown":
            area_dir = "_unknown"
        else:
            area_dir = area
        title = e.get("title") or Path(e["path"]).stem
        slug = slugify(title)
        target_area = area if area != "unknown" else "internals"
        target_path = f"docs/{target_area}/{slug}.md"
        repo_local = SOURCES_ROOT / e["repo"].split("/")[-1] / e["path"]
        questions = extract_questions(repo_local)
        backlog = {
            "title": title,
            "slug": slug,
            "area": area,
            "type": "hld-port",
            "target_path": target_path,
            "primary_sources": [
                {"repo": e["repo"], "path": e["path"], "ref": e["ref"]}
            ],
            "reader_questions": questions,
            "notes": f"size_bytes={e.get('size_bytes')}",
        }
        outdir = BACKLOG_DIR / area_dir
        outdir.mkdir(parents=True, exist_ok=True)
        # Avoid collisions
        outpath = outdir / f"{slug}.json"
        n = 2
        while outpath.exists():
            outpath = outdir / f"{slug}-{n}.json"
            n += 1
        outpath.write_text(json.dumps(backlog, indent=2, ensure_ascii=False) + "\n")
        by_area.setdefault(area_dir, 0)
        by_area[area_dir] += 1
    # Summary
    print(json.dumps(by_area, indent=2))


if __name__ == "__main__":
    main()
