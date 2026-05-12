#!/usr/bin/env python3
"""Measure link density of every docs page.

各ページについて

    density = (本文中の [text](url) リンク数) / 本文字数 * 1000

を計算し、極端に低い / 高いページを informational に report する。

* 低密度 (< 2 links / 1000 chars): 関連リンクが薄く、孤立気味のページ
* 高密度 (> 30 links / 1000 chars): リンク過多。glossary 自動注入の
  やりすぎや、ナビゲーション専用ページ等が紛れている可能性

加えて、``page_kind: split-child`` のページについては 2 層のナビゲーション
リンクを必須化する:

1. hub への戻りリンク 1 件以上
2. **同じ hub に属する他の split-child 全件** (concepts/operations/internals/
   limitations のうち、実ファイルとして存在し自分以外のもの) へのリンク

いずれかが欠落していれば warning として report する。本来の閾値より厳しめ
だが、サブページのナビゲーション健全性を担保するため。

本文の前処理:

* frontmatter (``---`` で挟まれた YAML ブロック) を除外
* HTML コメント ``<!-- ... -->`` を除外 (evidence 等)
* フェンス付きコードブロック ``` ``` / ``~~~`` を除外
* インラインコードスパン `` `...` `` を除外
* 残った本文中の ``[text](url)`` リンクを 1 件としてカウント
  (画像 ``![alt](url)`` は除外)

短いページ (本文 < 500 chars) は安定して測れないため評価対象外。

``meta/link-density-exceptions.json`` に
``{"exceptions": ["docs/path/to/page.md", ...]}`` を書くと個別除外できる。

Usage:
    python3 meta/scripts/check_link_density.py             # TSV を stdout
    python3 meta/scripts/check_link_density.py --report    # Markdown table
    python3 meta/scripts/check_link_density.py --check     # CI informational

Exit codes:
    0  always (informational), unless ``--strict-split-child`` is set and any
       split-child page is missing the hub or any sibling link, in which case
       the script exits with code 1 (CI gate).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
EXCEPTIONS = REPO_ROOT / "meta" / "link-density-exceptions.json"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Match inline [text](target) links, skip ![alt](url) images
LINK_RE = re.compile(r"(?<!\!)\[(?P<text>[^\]\n]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")

MIN_BODY_CHARS = 500
LOW_THRESHOLD = 2.0   # links / 1000 chars
HIGH_THRESHOLD = 30.0  # links / 1000 chars

# split-child suffix → strip these to obtain the parent hub slug
SPLIT_CHILD_SUFFIXES = ("-concepts", "-operations", "-internals", "-limitations")
PAGE_KIND_RE = re.compile(r"^page_kind:\s*([\w-]+)\s*$", re.MULTILINE)
# Optional frontmatter override:
#   hub: <basename-without-md>
# Used when the hub page does not follow the default naming convention
# (e.g. ``<base>-enhancement.md`` instead of ``<base>.md``).
HUB_OVERRIDE_RE = re.compile(r"^hub:\s*([\w./-]+?)\s*$", re.MULTILINE)


def load_exceptions() -> set[str]:
    if not EXCEPTIONS.exists():
        return set()
    try:
        data = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    except Exception:
        return set()
    return set(data.get("exceptions", []))


def strip_frontmatter(text: str) -> str:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text
    return text[m.end():]


def strip_code_and_comments(text: str) -> str:
    # Remove HTML comments first (may span lines, contain evidence blocks)
    text = HTML_COMMENT_RE.sub("", text)
    # Remove fenced code blocks line-by-line
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            continue
        if in_fence and stripped.startswith(fence_marker):
            in_fence = False
            continue
        if in_fence:
            continue
        out.append(line)
    body = "\n".join(out)
    # Strip inline code spans
    body = re.sub(r"`[^`\n]*`", "", body)
    return body


def extract_page_kind(text: str) -> str | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm = m.group(1)
    pk = PAGE_KIND_RE.search(fm)
    return pk.group(1) if pk else None


def extract_hub_override(text: str) -> str | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm = m.group(1)
    h = HUB_OVERRIDE_RE.search(fm)
    if not h:
        return None
    val = h.group(1).strip()
    if not val.endswith(".md"):
        val = val + ".md"
    return val


def split_child_hub_slug(md: Path) -> str | None:
    """Return the parent hub markdown filename for a split-child page, else None.

    split-child は ``<base>-{concepts,operations,internals,limitations}.md``
    の命名規約なので、suffix を剥がして ``<base>.md`` を返す。"""
    stem = md.stem
    for suffix in SPLIT_CHILD_SUFFIXES:
        if stem.endswith(suffix):
            return stem[: -len(suffix)] + ".md"
    return None


def check_split_child_links(
    md: Path, body: str, hub_override: str | None = None
) -> dict[str, object] | None:
    """Verify split-child page links to hub and ALL existing sibling split-children.

    2 層のリンクルール:

    * Layer 1: hub (``<base>.md``) への戻りリンク 1 件以上
    * Layer 2: 同じ hub の他の split-child (``<base>-<suffix>.md``) のうち
      **実ファイルとして存在するもの全件** へのリンクが揃っているか

    Returns ``{"has_hub": bool, "expected_siblings": set[str],
    "linked_siblings": set[str], "missing_siblings": set[str]}`` or ``None``
    if not a split-child page."""
    default_hub_filename = split_child_hub_slug(md)
    if default_hub_filename is None:
        return None
    # Frontmatter override takes precedence (for non-standard hub naming).
    hub_filename = hub_override or default_hub_filename
    # Sibling detection still uses the standard suffix-stripped base
    # (siblings always follow ``<base>-<suffix>.md`` regardless of hub name).
    base_stem = default_hub_filename[:-3]  # drop ".md"
    # Layer 2: detect actually-existing siblings on disk
    expected_siblings: set[str] = set()
    for suffix in SPLIT_CHILD_SUFFIXES:
        sib_stem = base_stem + suffix
        if sib_stem == md.stem:
            continue
        sib_path = md.parent / f"{sib_stem}.md"
        if sib_path.exists():
            expected_siblings.add(f"{sib_stem}.md")
    has_hub = False
    linked_siblings: set[str] = set()
    for m in LINK_RE.finditer(body):
        target = m.group("target")
        target_path = target.split("#", 1)[0].split("?", 1)[0]
        if not target_path:
            continue
        tail = target_path.rsplit("/", 1)[-1]
        if tail == hub_filename:
            has_hub = True
        elif tail in expected_siblings:
            linked_siblings.add(tail)
    missing_siblings = expected_siblings - linked_siblings
    return {
        "has_hub": has_hub,
        "expected_siblings": expected_siblings,
        "linked_siblings": linked_siblings,
        "missing_siblings": missing_siblings,
    }


def measure(md: Path) -> dict[str, object] | None:
    try:
        text = md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    page_kind = extract_page_kind(text)
    hub_override = extract_hub_override(text)
    body = strip_code_and_comments(strip_frontmatter(text))
    body_chars = len(body)
    if body_chars < MIN_BODY_CHARS:
        return None
    link_count = sum(1 for _ in LINK_RE.finditer(body))
    density = link_count / body_chars * 1000.0
    row: dict[str, object] = {
        "path": str(md.relative_to(REPO_ROOT)),
        "body_chars": body_chars,
        "link_count": link_count,
        "density": density,
        "page_kind": page_kind,
    }
    if page_kind == "split-child":
        sc = check_split_child_links(md, body, hub_override=hub_override)
        if sc is not None:
            row["split_child_has_hub"] = sc["has_hub"]
            row["split_child_expected_siblings"] = sc["expected_siblings"]
            row["split_child_linked_siblings"] = sc["linked_siblings"]
            row["split_child_missing_siblings"] = sc["missing_siblings"]
            # Layer 2 is satisfied iff every existing sibling is linked.
            # If there are zero expected siblings (lone split-child), treat
            # Layer 2 as vacuously satisfied.
            row["split_child_has_all_siblings"] = (
                len(sc["missing_siblings"]) == 0
            )
    return row


def collect() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    int,
    int,
]:
    """Return (low, high, split_child_warnings, total_evaluated, split_child_total)."""
    exceptions = load_exceptions()
    low: list[dict[str, object]] = []
    high: list[dict[str, object]] = []
    split_warns: list[dict[str, object]] = []
    total = 0
    split_total = 0
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(md.relative_to(REPO_ROOT))
        if rel in exceptions:
            continue
        row = measure(md)
        if row is None:
            continue
        total += 1
        if row["density"] < LOW_THRESHOLD:
            low.append(row)
        elif row["density"] > HIGH_THRESHOLD:
            high.append(row)
        if row.get("page_kind") == "split-child" and "split_child_has_hub" in row:
            split_total += 1
            if not (row["split_child_has_hub"] and row["split_child_has_all_siblings"]):
                split_warns.append(row)
    low.sort(key=lambda r: r["density"])
    high.sort(key=lambda r: r["density"], reverse=True)
    split_warns.sort(key=lambda r: r["path"])
    return low, high, split_warns, total, split_total


def render_tsv(
    low: list[dict[str, object]],
    high: list[dict[str, object]],
    split_warns: list[dict[str, object]],
) -> str:
    lines = ["bucket\tpath\tbody_chars\tlink_count\tdensity_per_1k\tnote"]
    for r in low:
        lines.append(
            f"low\t{r['path']}\t{r['body_chars']}\t{r['link_count']}\t{r['density']:.2f}\t"
        )
    for r in high:
        lines.append(
            f"high\t{r['path']}\t{r['body_chars']}\t{r['link_count']}\t{r['density']:.2f}\t"
        )
    for r in split_warns:
        missing: list[str] = []
        if not r.get("split_child_has_hub"):
            missing.append("hub")
        miss_sibs = sorted(r.get("split_child_missing_siblings") or [])
        if miss_sibs:
            missing.append("siblings:" + ",".join(miss_sibs))
        lines.append(
            f"split-child-warn\t{r['path']}\t{r['body_chars']}\t{r['link_count']}\t"
            f"{r['density']:.2f}\tmissing={'|'.join(missing)}"
        )
    return "\n".join(lines)


def render_report(
    low: list[dict[str, object]],
    high: list[dict[str, object]],
    split_warns: list[dict[str, object]],
    total: int,
    split_total: int,
) -> str:
    lines: list[str] = []
    lines.append("# link-density report")
    lines.append("")
    lines.append(
        f"Evaluated **{total}** pages (body >= {MIN_BODY_CHARS} chars). "
        f"Low threshold: < {LOW_THRESHOLD}/1k chars. "
        f"High threshold: > {HIGH_THRESHOLD}/1k chars."
    )
    lines.append("")
    lines.append(f"- low-density pages: **{len(low)}**")
    lines.append(f"- high-density pages: **{len(high)}**")
    lines.append(
        f"- split-child pages: **{split_total}** "
        f"(missing hub/sibling link: **{len(split_warns)}**)"
    )
    lines.append("")
    lines.append("## Low-density pages")
    lines.append("")
    lines.append(
        "関連リンクが薄く、孤立気味の可能性。Related links / Topics へのリンク追加候補。"
    )
    lines.append("")
    if low:
        lines.append("| path | body_chars | links | density (/1k) |")
        lines.append("|------|-----------:|------:|--------------:|")
        for r in low:
            lines.append(
                f"| `{r['path']}` | {r['body_chars']} | {r['link_count']} | {r['density']:.2f} |"
            )
    else:
        lines.append("_(none)_")
    lines.append("")
    lines.append("## High-density pages")
    lines.append("")
    lines.append(
        "リンク過多。Glossary 自動注入のやりすぎ、ナビ専用ページ、"
        "リスト過密などの可能性。"
    )
    lines.append("")
    if high:
        lines.append("| path | body_chars | links | density (/1k) |")
        lines.append("|------|-----------:|------:|--------------:|")
        for r in high:
            lines.append(
                f"| `{r['path']}` | {r['body_chars']} | {r['link_count']} | {r['density']:.2f} |"
            )
    else:
        lines.append("_(none)_")
    lines.append("")
    lines.append("## split-child pages missing hub / sibling link")
    lines.append("")
    lines.append(
        "``page_kind: split-child`` のページは 2 層のナビゲーションリンクを"
        "必須化している: (1) hub への戻りリンク 1 件以上, "
        "(2) 同じ hub の他 split-child のうち実ファイルとして存在するもの "
        "**全件** へのリンク。欠落しているページは導線が切れているため、"
        "本文に追記を推奨。"
    )
    lines.append("")
    if split_warns:
        lines.append("| path | missing | links | density (/1k) |")
        lines.append("|------|---------|------:|--------------:|")
        for r in split_warns:
            missing: list[str] = []
            if not r.get("split_child_has_hub"):
                missing.append("hub")
            miss_sibs = sorted(r.get("split_child_missing_siblings") or [])
            if miss_sibs:
                missing.append("siblings: " + ", ".join(miss_sibs))
            lines.append(
                f"| `{r['path']}` | {'<br>'.join(missing)} | "
                f"{r['link_count']} | {r['density']:.2f} |"
            )
    else:
        lines.append("_(none)_")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI informational モード。件数を stderr に出して 0 で終了する。",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Markdown 形式の詳細レポートを stdout に出す。",
    )
    parser.add_argument(
        "--strict-split-child",
        action="store_true",
        help=(
            "split-child のリンクルール (hub + 全 sibling) 違反が 1 件でもあれば "
            "exit code 1 で終了する CI gate モード。density 閾値は引き続き "
            "informational。"
        ),
    )
    args = parser.parse_args()

    low, high, split_warns, total, split_total = collect()

    if args.check or args.strict_split_child:
        gate = "strict" if args.strict_split_child else "informational"
        print(
            f"[link-density] evaluated {total} pages: "
            f"{len(low)} low-density (< {LOW_THRESHOLD}/1k), "
            f"{len(high)} high-density (> {HIGH_THRESHOLD}/1k); "
            f"split-child {split_total} pages, "
            f"{len(split_warns)} missing hub/sibling link ({gate})",
            file=sys.stderr,
        )
        if args.strict_split_child and split_warns:
            for r in split_warns:
                missing: list[str] = []
                if not r.get("split_child_has_hub"):
                    missing.append("hub")
                miss_sibs = sorted(r.get("split_child_missing_siblings") or [])
                if miss_sibs:
                    missing.append("siblings:" + ",".join(miss_sibs))
                print(
                    f"  - {r['path']}: missing {' | '.join(missing)}",
                    file=sys.stderr,
                )
            return 1
        return 0

    if args.report:
        print(render_report(low, high, split_warns, total, split_total))
        return 0

    print(render_tsv(low, high, split_warns))
    return 0


if __name__ == "__main__":
    sys.exit(main())
