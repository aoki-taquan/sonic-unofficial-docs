#!/usr/bin/env python3
"""Refresh `sources[].ref` SHA in page frontmatter against local cache.

`docs/**/*.md` の frontmatter `sources[].ref` を、対応する
`.cache/sonic-sources/<repo>/` の現在の HEAD SHA に一括更新する保守スクリプト。

CI には組み込まない（オフライン環境では cache が無いため、運用者が手動実行）。

仕様:
  - `sources[].repo` (例: ``sonic-net/SONiC``) を repo path 名 (例: ``SONiC``) に
    変換し、`.cache/sonic-sources/<name>/.git` の `git rev-parse HEAD` を取得
  - ページ内のいずれかの `sources[].ref` が cache HEAD と異なれば書き換え
  - 書き換えたページは `last_verified` を今日 (TODAY) に更新
  - `verification` ステータスは触らない（昇格判定は別フロー）
  - デフォルト: 1 リポ・最大 30 ページずつ動かす（衝突回避）

Usage:
    python3 meta/scripts/refresh_sources_sha.py --dry-run
    python3 meta/scripts/refresh_sources_sha.py --repos SONiC --max-pages 30
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"
TODAY = date(2026, 5, 13).isoformat()


def _resolve_cache_root() -> Path:
    """Locate `.cache/sonic-sources/` — fall back to git common dir when run from a worktree."""
    primary = REPO_ROOT / ".cache" / "sonic-sources"
    if primary.exists():
        return primary
    git_marker = REPO_ROOT / ".git"
    if git_marker.is_file():
        text = git_marker.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            gitdir = Path(text.split(":", 1)[1].strip())
            common = gitdir.parent.parent
            if common.name == ".git":
                cand = common.parent / ".cache" / "sonic-sources"
                if cand.exists():
                    return cand
    return primary


CACHE_ROOT = _resolve_cache_root()


def git_head(cache_dir: Path) -> str | None:
    """Return current HEAD SHA of cache_dir, or None if not a git repo."""
    if not (cache_dir / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(cache_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode != 0:
            return None
        sha = out.stdout.strip()
        return sha if sha else None
    except FileNotFoundError:
        return None


def repo_short_name(full: str) -> str:
    """Convert ``sonic-net/SONiC`` → ``SONiC``."""
    return full.split("/")[-1]


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def split_frontmatter(text: str) -> tuple[str, str] | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return m.group(1), text[m.end() :]


# Minimal YAML-like editor: we deliberately edit raw lines instead of
# round-tripping via PyYAML to preserve quoting / ordering / comments.

REPO_LINE_RE = re.compile(r"^(\s*)-?\s*repo:\s*(\S+)\s*$")
REF_LINE_RE = re.compile(r"^(\s*)ref:\s*(\S+)\s*$")
LAST_VERIFIED_RE = re.compile(r"^(last_verified:\s*)(\S+)\s*$", re.MULTILINE)


def collect_repos_in_frontmatter(fm: str) -> list[str]:
    repos: list[str] = []
    for line in fm.splitlines():
        m = REPO_LINE_RE.match(line)
        if m:
            repos.append(m.group(2).strip().strip('"').strip("'"))
    return repos


def refresh_frontmatter(fm: str, head_by_repo: dict[str, str]) -> tuple[str, list[tuple[str, str, str]]]:
    """Walk frontmatter line-by-line; rewrite each `ref:` based on its preceding `repo:`.

    Returns (new_fm, changes) where changes is a list of (repo, old_ref, new_ref).
    """
    lines = fm.splitlines(keepends=False)
    out: list[str] = []
    current_repo: str | None = None
    changes: list[tuple[str, str, str]] = []
    in_sources = False

    for line in lines:
        stripped = line.lstrip()
        len(line) - len(stripped)
        # Detect entering / leaving `sources:` block
        if re.match(r"^sources:\s*$", line):
            in_sources = True
            out.append(line)
            continue
        if in_sources and stripped and not line.startswith(" ") and not line.startswith("\t"):
            # back to top-level field → out of sources
            in_sources = False
            current_repo = None

        if in_sources:
            mrepo = REPO_LINE_RE.match(line)
            if mrepo:
                current_repo = mrepo.group(2).strip().strip('"').strip("'")
                out.append(line)
                continue
            mref = REF_LINE_RE.match(line)
            if mref and current_repo is not None:
                old_ref = mref.group(2).strip().strip('"').strip("'")
                short = repo_short_name(current_repo)
                head = head_by_repo.get(short)
                if head and head != old_ref:
                    changes.append((current_repo, old_ref, head))
                    out.append(f"{mref.group(1)}ref: {head}")
                    continue
        out.append(line)

    new_fm = "\n".join(out)
    return new_fm, changes


def update_last_verified(fm: str, today: str) -> str:
    def _sub(m: re.Match[str]) -> str:
        return f"{m.group(1)}{today}"

    new_fm, n = LAST_VERIFIED_RE.subn(_sub, fm, count=1)
    if n == 0:
        # No `last_verified:` line — leave fm alone (frontmatter_lint will flag it)
        return fm
    return new_fm


def iter_pages(docs_root: Path):
    for path in sorted(docs_root.rglob("*.md")):
        yield path


def process(
    *,
    dry_run: bool,
    max_pages: int,
    repo_filter: set[str] | None,
) -> int:
    if not CACHE_ROOT.exists():
        print(f"[warn] cache root not found: {CACHE_ROOT}", file=sys.stderr)
        print("       run from a checkout that has `.cache/sonic-sources/` populated.", file=sys.stderr)
        return 0

    head_by_repo: dict[str, str] = {}
    for child in sorted(CACHE_ROOT.iterdir()):
        if not child.is_dir():
            continue
        if repo_filter and child.name not in repo_filter:
            continue
        sha = git_head(child)
        if sha:
            head_by_repo[child.name] = sha
        else:
            print(f"[skip] {child.name}: not a git checkout", file=sys.stderr)

    if not head_by_repo:
        print("[warn] no cache repos resolved; nothing to do.", file=sys.stderr)
        return 0

    print(f"[info] resolved {len(head_by_repo)} cache repos:")
    for name, sha in head_by_repo.items():
        print(f"  - {name}: {sha[:12]}")

    touched = 0
    for path in iter_pages(DOCS_ROOT):
        if touched >= max_pages:
            break
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        split = split_frontmatter(text)
        if not split:
            continue
        fm, body = split

        # Quick filter: must reference at least one of the targeted repos
        page_repos = {repo_short_name(r) for r in collect_repos_in_frontmatter(fm)}
        if not page_repos & set(head_by_repo.keys()):
            continue

        new_fm, changes = refresh_frontmatter(fm, head_by_repo)
        if not changes:
            continue

        rel = path.relative_to(REPO_ROOT)
        print(f"[update] {rel}")
        for repo, old, new in changes:
            print(f"    {repo}: {old[:12]} -> {new[:12]}")

        if dry_run:
            touched += 1
            continue

        new_fm = update_last_verified(new_fm, TODAY)
        path.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")
        touched += 1

    print(f"[done] {'would update' if dry_run else 'updated'} {touched} page(s)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="show changes without writing")
    p.add_argument("--max-pages", type=int, default=30, help="maximum pages to update per run (default: 30)")
    p.add_argument(
        "--repos",
        type=str,
        default="SONiC",
        help="comma-separated cache-dir names to target (default: SONiC). use 'all' to target every cached repo.",
    )
    args = p.parse_args()

    repo_filter: set[str] | None
    if args.repos.strip().lower() == "all":
        repo_filter = None
    else:
        repo_filter = {r.strip() for r in args.repos.split(",") if r.strip()}

    return process(dry_run=args.dry_run, max_pages=args.max_pages, repo_filter=repo_filter)


if __name__ == "__main__":
    sys.exit(main())
