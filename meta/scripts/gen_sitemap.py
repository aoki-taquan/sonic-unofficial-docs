#!/usr/bin/env python3
"""Generate docs/_meta/sitemap.md from the documentation tree.

`docs/**/*.md` を walk し、各ディレクトリの `.pages`（mkdocs-awesome-pages
プラグイン用）に従って mkdocs nav 順で全ページを階層付き列挙する。
各ページの `title` / `verification` / `description` を frontmatter から拾い、
Markdown のネストされた箇条書きとして書き出す。

Usage:
    .venv/bin/python3 meta/scripts/gen_sitemap.py
    .venv/bin/python3 meta/scripts/gen_sitemap.py --check
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
OUTPUT = DOCS_DIR / "_meta" / "sitemap.md"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# verification 値 -> Material admonition 風の短い badge ラベル
BADGE = {
    "code-verified": "[code-verified]",
    "runbook-verified": "[runbook-verified]",
    "discrepancy-found": "[discrepancy-found]",
    "issue-confirmed": "[issue-confirmed]",
    "hld-only": "[hld-only]",
    "meta": "[meta]",
    "stub": "[stub]",
}

# 説明の短縮上限（文字数）
DESC_MAX = 80


def parse_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def parse_pages(pages_path: Path) -> tuple[str | None, list[str], bool, bool]:
    """Return (title, nav_entries, has_wildcard, hidden)."""
    try:
        with pages_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return None, [], False, False
    if not isinstance(data, dict):
        return None, [], False, False
    title = data.get("title")
    hidden = bool(data.get("hide"))
    raw_nav = data.get("nav") or []
    entries: list[str] = []
    wildcard = False

    def walk(items: list) -> None:
        nonlocal wildcard
        for item in items:
            if isinstance(item, dict):
                for _, v in item.items():
                    if isinstance(v, str):
                        if v.strip() == "...":
                            wildcard = True
                        else:
                            entries.append(v.strip())
                    elif isinstance(v, list):
                        walk(v)
            elif isinstance(item, str):
                if item.strip() == "...":
                    wildcard = True
                else:
                    entries.append(item.strip())

    walk(raw_nav)
    return title, entries, wildcard, hidden


def shorten(s: str, n: int = DESC_MAX) -> str:
    s = " ".join(s.split())
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def md_link(path: Path, label: str) -> str:
    rel = path.relative_to(DOCS_DIR).as_posix()
    # docs/_meta/sitemap.md からの相対リンク
    OUTPUT.parent.relative_to(DOCS_DIR).as_posix()  # "_meta"
    # 親（docs/）に上がってから path へ
    target = "../" + rel
    return f"[{label}]({target})"


def render_md_entry(md: Path, depth: int) -> str:
    fm = parse_frontmatter(md)
    title = str(fm.get("title") or md.stem).strip() or md.stem
    verification = str(fm.get("verification") or "stub").strip() or "stub"
    badge = BADGE.get(verification, f"[{verification}]")
    description = fm.get("description") or ""
    if not isinstance(description, str):
        description = str(description)
    desc = shorten(description) if description else ""
    indent = "  " * depth
    link = md_link(md, title)
    if desc:
        return f"{indent}- {link} — {badge} {desc}"
    return f"{indent}- {link} — {badge}"


def render_dir_header(directory: Path, depth: int) -> str:
    pages = directory / ".pages"
    title = None
    if pages.exists():
        title, _entries, _wc, _hidden = parse_pages(pages)
    if not title:
        title = directory.name
    indent = "  " * depth
    return f"{indent}- **{title}** (`{directory.relative_to(DOCS_DIR).as_posix()}/`)"


def walk_dir(directory: Path, depth: int, lines: list[str], counter: list[int]) -> None:
    """Recursively emit nav-order listing for a directory.

    `.pages` の `nav:` 順を尊重。未列挙のファイル/ディレクトリは末尾に
    アルファベット順で追加（awesome-pages の wildcard 相当のデフォルト挙動）。
    """
    pages = directory / ".pages"
    nav_entries: list[str] = []
    wildcard = True  # .pages なしならデフォルトでアルファベット順全列挙
    hidden = False
    if pages.exists():
        _t, nav_entries, wildcard, hidden = parse_pages(pages)
        # .pages に hide: true があってもサイトマップでは列挙する（メタ用途）

    # ディレクトリ内の md/ サブディレクトリ
    md_files = {p.name: p for p in directory.iterdir() if p.is_file() and p.suffix == ".md"}
    subdirs = {
        p.name: p
        for p in directory.iterdir()
        if p.is_dir() and not p.name.startswith(".") and any(p.rglob("*.md"))
    }

    listed: set[str] = set()
    # nav 順に出力
    for entry in nav_entries:
        if entry in md_files:
            lines.append(render_md_entry(md_files[entry], depth))
            counter[0] += 1
            listed.add(entry)
        elif entry in subdirs:
            lines.append(render_dir_header(subdirs[entry], depth))
            walk_dir(subdirs[entry], depth + 1, lines, counter)
            listed.add(entry)
        else:
            # 存在しない（check_pages_integrity が拾うので警告のみ）
            continue

    # 残り（wildcard or .pages 無し）
    if wildcard or not pages.exists():
        for name in sorted(md_files.keys()):
            if name in listed:
                continue
            lines.append(render_md_entry(md_files[name], depth))
            counter[0] += 1
        for name in sorted(subdirs.keys()):
            if name in listed:
                continue
            lines.append(render_dir_header(subdirs[name], depth))
            walk_dir(subdirs[name], depth + 1, lines, counter)


def render() -> tuple[str, int]:
    counter = [0]
    body: list[str] = []
    # docs/ 直下から
    walk_dir(DOCS_DIR, 0, body, counter)

    total = counter[0]

    header = [
        "---",
        "title: サイトマップ",
        f'description: "サイトマップ — docs/**/*.md を mkdocs nav 順で階層列挙したインデックス（全 {total} ページ）。meta/scripts/gen_sitemap.py で自動生成。"',
        "verification: meta",
        "last_verified: 2026-05-11",
        "hide:",
        "  - toc",
        "tags:",
        "  - meta",
        "  - sitemap",
        "---",
        "",
        "# サイトマップ",
        "",
        "このページは `docs/**/*.md` を mkdocs nav 順 (`.pages` 準拠) で階層列挙した"
        "インデックスです。`meta/scripts/gen_sitemap.py` で自動生成されます。",
        "",
        f"全 **{total}** ページ。各エントリは "
        "`タイトル — [verification badge] description (短縮)` の形式で並びます。",
        "",
        "- ページ数の状態別内訳は [カバレッジ](coverage.md) を参照。",
        "- 実装との乖離が確認されたページは "
        "[discrepancy index](../reference/verification/discrepancy-index.md) を参照。",
        "",
        "## 全ページ（nav 順）",
        "",
    ]
    text = "\n".join(header + body) + "\n"
    return text, total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="差分があれば exit 1（CI 用、書き込みはしない）",
    )
    args = parser.parse_args()

    new_text, total = render()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if args.check:
        original = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if original != new_text:
            print(
                "ERROR: docs/_meta/sitemap.md が古い。"
                "`python3 meta/scripts/gen_sitemap.py` を実行して commit すること。",
                file=sys.stderr,
            )
            import difflib

            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile="sitemap.md (現状)",
                tofile="sitemap.md (期待)",
                n=3,
            )
            sys.stderr.writelines(diff)
            return 1
        print(f"OK: sitemap は最新 ({total} pages)")
        return 0

    OUTPUT.write_text(new_text, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)} ({total} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
