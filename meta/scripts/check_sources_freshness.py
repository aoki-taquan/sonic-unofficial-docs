#!/usr/bin/env python3
"""Check freshness of pinned SONiC sources against local cache.

`meta/index/repos.json` で固定している commit SHA と、
`.cache/sonic-sources/<repo>/` の実 git HEAD / `origin/master`（無ければ `origin/main`）
を突き合わせ、各リポについて以下を表で出す:

  - repos.json の SHA（pinned）
  - ローカル cache の HEAD SHA
  - upstream の HEAD SHA
  - pinned から upstream までの commit 差分件数 (behind by)
  - pinned commit の last-commit-date

ローカル cache が無いリポは skip して warning。
CI には組み込まない（オフライン環境では cache が無いため）。

Usage:
    python3 meta/scripts/check_sources_freshness.py             # 表を stdout
    python3 meta/scripts/check_sources_freshness.py --check     # 遅延サマリを stderr に追加
    python3 meta/scripts/check_sources_freshness.py --write     # docs ページ生成
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPOS_JSON = REPO_ROOT / "meta" / "index" / "repos.json"


def _resolve_cache_root() -> Path:
    """Locate `.cache/sonic-sources/` — fall back to git common dir when run from a worktree."""
    primary = REPO_ROOT / ".cache" / "sonic-sources"
    if primary.exists():
        return primary
    # Worktree fallback: read .git file to find common dir
    git_marker = REPO_ROOT / ".git"
    if git_marker.is_file():
        text = git_marker.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            gitdir = Path(text.split(":", 1)[1].strip())
            # gitdir like <main>/.git/worktrees/<name> → common dir is gitdir/../..
            common = gitdir.parent.parent
            if common.name == ".git":
                cand = common.parent / ".cache" / "sonic-sources"
                if cand.exists():
                    return cand
    return primary


CACHE_ROOT = _resolve_cache_root()
OUTPUT_MD = REPO_ROOT / "docs" / "reference" / "verification" / "sources-freshness.md"
PAGES_FILE = REPO_ROOT / "docs" / "reference" / "verification" / ".pages"


def git(cache_dir: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(cache_dir), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except FileNotFoundError:
        return None


def short(sha: str | None) -> str:
    if not sha:
        return "—"
    return sha[:12]


def gather() -> list[dict[str, object]]:
    repos = json.loads(REPOS_JSON.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for entry in repos:
        if not entry.get("included", True):
            continue
        repo_full = entry["repo"]  # "sonic-net/<name>"
        pinned = entry.get("ref") or entry.get("sha") or ""
        repo_name = repo_full.split("/", 1)[1]
        cache_dir = CACHE_ROOT / repo_name
        row: dict[str, object] = {
            "repo": repo_full,
            "pinned": pinned,
            "cache_head": None,
            "upstream_head": None,
            "upstream_ref": None,
            "behind": None,
            "pinned_date": None,
            "note": "",
        }
        if not cache_dir.exists():
            row["note"] = "cache missing"
            print(f"warning: cache missing for {repo_full} ({cache_dir})", file=sys.stderr)
            rows.append(row)
            continue
        row["cache_head"] = git(cache_dir, "rev-parse", "HEAD")
        # upstream ref: try origin/master then origin/main
        upstream_ref = None
        for cand in ("origin/master", "origin/main"):
            sha = git(cache_dir, "rev-parse", cand)
            if sha:
                upstream_ref = cand
                row["upstream_head"] = sha
                break
        row["upstream_ref"] = upstream_ref
        if upstream_ref and pinned:
            # 差分: pinned..upstream
            count = git(cache_dir, "rev-list", f"{pinned}..{upstream_ref}", "--count")
            if count is not None and count.isdigit():
                row["behind"] = int(count)
            else:
                row["note"] = "behind計測不可（shallow clone で pinned が見えない可能性）"
        if pinned:
            d = git(cache_dir, "log", "-1", "--format=%cI", pinned)
            if d:
                row["pinned_date"] = d[:10]
        rows.append(row)
    return rows


def render_table(rows: list[dict[str, object]]) -> str:
    lines = [
        "| repo | repos.json SHA | cache HEAD | upstream HEAD | behind by | pinned commit date | note |",
        "|------|----------------|------------|---------------|-----------|--------------------|------|",
    ]
    for r in rows:
        behind = r["behind"]
        behind_s = "0" if behind == 0 else (str(behind) if isinstance(behind, int) else "—")
        up_ref = r.get("upstream_ref") or ""
        up_label = f"{short(r['upstream_head'])}" + (f" ({up_ref})" if up_ref else "")
        lines.append(
            "| `{repo}` | `{pinned}` | `{head}` | {up} | {behind} | {date} | {note} |".format(
                repo=r["repo"],
                pinned=short(r["pinned"]),  # type: ignore[arg-type]
                head=short(r["cache_head"]),  # type: ignore[arg-type]
                up=up_label,
                behind=behind_s,
                date=r["pinned_date"] or "—",
                note=r["note"] or "",
            )
        )
    return "\n".join(lines)


def write_page(rows: list[dict[str, object]]) -> None:
    today = date.today().isoformat()
    total = len(rows)
    behind_repos = [r for r in rows if isinstance(r["behind"], int) and r["behind"] > 0]
    missing = [r for r in rows if r["note"] == "cache missing"]
    body = f"""---
title: ソース pinned SHA の新鮮度（sources-freshness）
description: "ソース pinned SHA の新鮮度（sources-freshness） — meta/index/repos.json で固定している commit SHA と各リポの upstream HEAD を突き合わせ、本サイトのスナップショットがどれだけ master から遅れているかを一覧化する。"
verification: meta
last_verified: {today}
tags:
  - verification
  - sources
---

# ソース pinned SHA の新鮮度（sources-freshness）

本サイトの各ページは frontmatter `sources[].ref` で SONiC 上流リポのコミット SHA を**固定**している。固定 SHA は `meta/index/repos.json` で一元管理しており、Indexer 再走時に更新される。

このページは `meta/scripts/check_sources_freshness.py --write` で生成され、各対象リポについて pinned SHA と upstream HEAD の差分を可視化する。**読者はサイトの記述がどの時点の SONiC master を反映しているかをここで確認できる**。

!!! info "生成時刻 / generated-at"
    この表は **{today}** に `check_sources_freshness.py --write` で生成された。`cache HEAD` と `upstream HEAD` は **生成時点** のローカル shallow clone を反映する。表の `cache HEAD` 列がページ上 frontmatter `last_verified` から大きく時間が空いている場合、本ページ自体が陳腐化している可能性がある（その場合は再生成スクリプトを走らせること）。

## サマリ

- 対象リポ数: **{total}**
- upstream より遅れているリポ: **{len(behind_repos)}**
- ローカル cache が見つからなかったリポ: **{len(missing)}**
- 生成日（last regenerated）: **{today}**

## 一覧

{render_table(rows)}

- `repos.json SHA`: `meta/index/repos.json` に記録されている pinned SHA（本サイトのスナップショット基準）
- `cache HEAD`: `.cache/sonic-sources/<repo>/` ローカル shallow clone の現在 HEAD
- `upstream HEAD`: ローカル clone から見える `origin/master`（無ければ `origin/main`）の HEAD
- `behind by`: pinned から upstream までの commit 数（`git rev-list pinned..upstream --count`）。shallow clone の都合で `pinned` がローカルに居ないと計測不能になる場合がある

## 運用注記

- 定期的に **Indexer を再走させて `meta/index/repos.json` を更新する**（四半期サイクル目安）。更新後は本ページを `python3 meta/scripts/check_sources_freshness.py --write` で再生成する。
- 個別ページの `sources[].ref` は当該ページの裏取り時点で固定する設計であり、サイト全体で一斉に SHA を bump する必要はない。本ページはあくまで「サイト全体としてどの時点の master を見ているか」の俯瞰指標。
- 詳細手順は `meta/discrepancy-operations.md` の「定期実行」節を参照。
"""
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(body, encoding="utf-8")
    update_pages_nav()


def update_pages_nav() -> None:
    if not PAGES_FILE.exists():
        return
    text = PAGES_FILE.read_text(encoding="utf-8")
    if "sources-freshness.md" in text:
        return
    # 末尾に追記
    if not text.endswith("\n"):
        text += "\n"
    text += "  - sources-freshness.md\n"
    PAGES_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="docs ページを生成する")
    ap.add_argument("--check", action="store_true", help="遅延サマリを stderr に出力")
    ap.add_argument(
        "--threshold",
        type=int,
        default=1,
        help="--check で何 commit 以上遅れていたら警告するか（既定: 1）",
    )
    args = ap.parse_args()

    rows = gather()
    print(render_table(rows))

    if args.check:
        behind = [
            r for r in rows
            if isinstance(r["behind"], int) and r["behind"] >= args.threshold
        ]
        if behind:
            commit_sum = sum(int(r["behind"]) for r in behind)  # type: ignore[arg-type]
            print(
                f"info: {len(behind)} リポが {args.threshold} commit 以上遅れています "
                f"（合計 {commit_sum} commits behind）",
                file=sys.stderr,
            )
        else:
            print("info: すべての対象リポは upstream に追随しています", file=sys.stderr)

    if args.write:
        write_page(rows)
        print(f"wrote {OUTPUT_MD}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
