#!/usr/bin/env python3
"""Built HTML quality check.

`mkdocs build --strict` で生成された `site/` 配下の .html を走査し、
以下の品質シグナルを検出する:

- ページ単位の `<title>` 不在
- `<h1>` がページに 2 つ以上 (重複) / 0 個 (欠如)
- 空の `<a href="">` (anchor だけで href が空)
- 空の `<img src="">`
- 空コードブロック `<pre><code></code></pre>`
- mermaid placeholder 残骸 (`<pre><code class="language-mermaid">`
  のまま mermaid 化されず生コードで残るケースなど)

検出結果は `meta/built-html-report.md` に保存する。

CI 上では informational 用途で `|| true` で呼ばれる想定。スクリプト自体は
高優先 (h1 重複, 空 a/img) のカウントが 0 でなければ exit 1、それ以外は 0
を返す `--strict-high` モードも備える。デフォルトは exit 0。
"""

from __future__ import annotations

import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SITE = REPO_ROOT / "site"
DEFAULT_REPORT = REPO_ROOT / "meta" / "built-html-report.md"


class PageStats(HTMLParser):
    """軽量な HTML パーサ。問題箇所だけ拾う。

    BeautifulSoup を入れずに stdlib だけで済ませる。`html.parser` は
    self-closing や属性順を気にしないので、検出用途には十分。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_count = 0
        self.h1_count = 0
        self.empty_a = 0
        self.empty_img = 0
        # `<pre><code></code></pre>` 検出用フラグ
        self._in_pre = False
        self._in_code = False
        self._code_has_content = False
        self.empty_codeblocks = 0
        # mermaid placeholder 残骸 (mkdocs-mermaid2 が描画前の class 名を残す)
        self.mermaid_residue = 0
        # `<main>` 内に限定するためのカウンタ
        self._main_depth = 0

    # --- helpers --------------------------------------------------------
    def _in_main(self) -> bool:
        # `<main>` が無いページ (404 等) はページ全体を対象にする
        return self._main_depth > 0 or self._main_depth == 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs}
        if tag == "title":
            self.title_count += 1
        elif tag == "main":
            self._main_depth += 1
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "a":
            href = attr_dict.get("href")
            # `href` 属性が存在し、かつ trim して空
            if href is not None and href.strip() == "":
                self.empty_a += 1
        elif tag == "img":
            src = attr_dict.get("src")
            if src is not None and src.strip() == "":
                self.empty_img += 1
        elif tag == "pre":
            self._in_pre = True
        elif tag == "code":
            if self._in_pre:
                self._in_code = True
                self._code_has_content = False
            cls = attr_dict.get("class", "")
            if "language-mermaid" in cls:
                # mermaid2 が SVG 化に成功すると `<pre class="mermaid">...`
                # に置換される。`<code class="language-mermaid">` がそのまま
                # 残っていれば描画失敗の痕跡。
                self.mermaid_residue += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "main" and self._main_depth > 0:
            self._main_depth -= 1
        elif tag == "code" and self._in_code:
            if self._in_pre and not self._code_has_content:
                self.empty_codeblocks += 1
            self._in_code = False
        elif tag == "pre":
            self._in_pre = False

    def handle_data(self, data: str) -> None:
        if self._in_code and data.strip():
            self._code_has_content = True


def scan_file(path: Path) -> dict[str, int]:
    parser = PageStats()
    try:
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        # パース失敗もシグナルとして残す
        return {"parse_error": 1, "_msg": str(exc)}
    return {
        "title_missing": 0 if parser.title_count > 0 else 1,
        "h1_missing": 0 if parser.h1_count >= 1 else 1,
        "h1_duplicated": 1 if parser.h1_count >= 2 else 0,
        "empty_a": parser.empty_a,
        "empty_img": parser.empty_img,
        "empty_codeblock": parser.empty_codeblocks,
        "mermaid_residue": parser.mermaid_residue,
        "h1_count": parser.h1_count,
    }


def walk_site(site_root: Path) -> list[tuple[Path, dict[str, int]]]:
    rows: list[tuple[Path, dict[str, int]]] = []
    for html in sorted(site_root.rglob("*.html")):
        # mkdocs が出す 404.html / search/ などはスキップせず全部見る
        stats = scan_file(html)
        rows.append((html, stats))
    return rows


HIGH_KEYS = ("h1_duplicated", "empty_a", "empty_img")
LOW_KEYS = ("title_missing", "h1_missing", "empty_codeblock", "mermaid_residue")


def aggregate(rows: list[tuple[Path, dict[str, int]]]) -> dict[str, int]:
    totals: dict[str, int] = {k: 0 for k in HIGH_KEYS + LOW_KEYS}
    totals["pages"] = len(rows)
    for _path, stats in rows:
        for k in HIGH_KEYS + LOW_KEYS:
            totals[k] += stats.get(k, 0)
    return totals


def render_report(rows: list[tuple[Path, dict[str, int]]], site_root: Path) -> str:
    totals = aggregate(rows)
    lines: list[str] = []
    lines.append("# Built HTML quality report")
    lines.append("")
    lines.append(
        "`mkdocs build --strict` 後の `site/` を `meta/scripts/check_built_html.py` で走査した結果。"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- pages scanned: **{totals['pages']}**")
    lines.append("")
    lines.append("### High priority")
    lines.append("")
    lines.append(f"- `<h1>` duplicated pages: **{totals['h1_duplicated']}**")
    lines.append(f"- empty `<a href=\"\">`: **{totals['empty_a']}**")
    lines.append(f"- empty `<img src=\"\">`: **{totals['empty_img']}**")
    lines.append("")
    lines.append("### Low priority (report only)")
    lines.append("")
    lines.append(f"- `<title>` missing: **{totals['title_missing']}**")
    lines.append(f"- `<h1>` missing: **{totals['h1_missing']}**")
    lines.append(f"- empty `<pre><code></code></pre>`: **{totals['empty_codeblock']}**")
    lines.append(f"- mermaid placeholder residue: **{totals['mermaid_residue']}**")
    lines.append("")

    # per-page detail (only pages with any signal)
    detail: list[tuple[Path, dict[str, int]]] = [
        (p, s) for p, s in rows if any(s.get(k, 0) for k in HIGH_KEYS + LOW_KEYS)
    ]
    lines.append(f"## Pages with any signal ({len(detail)})")
    lines.append("")
    if not detail:
        lines.append("- (none)")
    else:
        lines.append("| page | h1_dup | empty_a | empty_img | title_miss | h1_miss | empty_code | mermaid_residue |")
        lines.append("|------|-------:|-------:|---------:|----------:|--------:|-----------:|----------------:|")
        for path, s in detail:
            rel = path.relative_to(site_root).as_posix()
            lines.append(
                "| `{p}` | {a} | {b} | {c} | {d} | {e} | {f} | {g} |".format(
                    p=rel,
                    a=s.get("h1_duplicated", 0),
                    b=s.get("empty_a", 0),
                    c=s.get("empty_img", 0),
                    d=s.get("title_missing", 0),
                    e=s.get("h1_missing", 0),
                    f=s.get("empty_codeblock", 0),
                    g=s.get("mermaid_residue", 0),
                )
            )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site", type=Path, default=DEFAULT_SITE,
                    help="built site directory (default: site/)")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT,
                    help="output report path")
    ap.add_argument("--strict-high", action="store_true",
                    help="exit 1 if any high-priority signal > 0")
    args = ap.parse_args()

    if not args.site.exists():
        print(f"[check_built_html] site not found: {args.site}", file=sys.stderr)
        print("  -> run `mkdocs build --strict` first.", file=sys.stderr)
        return 1

    rows = walk_site(args.site)
    report = render_report(rows, args.site)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")

    totals = aggregate(rows)
    print(
        f"[check_built_html] pages={totals['pages']} "
        f"high(h1_dup={totals['h1_duplicated']}, empty_a={totals['empty_a']}, "
        f"empty_img={totals['empty_img']}) "
        f"low(title_miss={totals['title_missing']}, h1_miss={totals['h1_missing']}, "
        f"empty_code={totals['empty_codeblock']}, mermaid={totals['mermaid_residue']})"
    )
    print(f"[check_built_html] report -> {args.report.relative_to(REPO_ROOT)}")

    if args.strict_high and any(totals[k] for k in HIGH_KEYS):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
