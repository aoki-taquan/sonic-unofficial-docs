#!/usr/bin/env python3
"""Frontmatter linter for docs/**/*.md (v2).

v1 checks (kept):
  a) verification in {hld-only, code-verified, discrepancy-found} -> sources non-empty
  b) verification == code-verified -> body does not start with '!!! warning "HLD-only"'
  c) verification == discrepancy-found -> body contains a "実装との乖離" section
  d) last_verified matches YYYY-MM-DD
  e) title non-empty, area is a known enum
  f) monitor in {not_implemented, evolved_beyond_hld, partially_implemented, deprecated};
     verification == discrepancy-found -> monitor field must be present

v2 additions:
  g) mojibake / non-ASCII control character detection (excludes TAB/LF/CR);
     Unicode replacement char (U+FFFD); classic UTF-8-as-Latin-1 mojibake patterns
  h) sources[].path liveness check against `.cache/sonic-sources/<repo-name>/<path>`.
     Skipped automatically when the cache directory is absent (e.g. CI runners) so
     that the check does not flake. Force-enable via FRONTMATTER_LINT_CHECK_PATHS=1.
  i) description field is optional but recommended (warn-only). Used by
     mkdocs-material to populate the `<meta name="description">` tag for SEO.
     Generate missing values with `python meta/scripts/gen_descriptions.py`.

Output: meta/frontmatter-lint-report.md     (v1-compatible, hard violations only)
        meta/frontmatter-lint-report-v2.md  (v2 enhanced: hard + warnings)
Exit code: 1 if any HARD violation (a-g), else 0. Path-liveness (h) only warns.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
CACHE_DIR = REPO_ROOT / ".cache" / "sonic-sources"
REPORT_PATH = REPO_ROOT / "meta" / "frontmatter-lint-report.md"
REPORT_V2_PATH = REPO_ROOT / "meta" / "frontmatter-lint-report-v2.md"

VALID_AREAS = {
    "routing", "switching", "overlay", "acl-qos", "system",
    "management", "platform", "architecture", "internals", "reference",
}
VERIFICATIONS_REQUIRING_SOURCES = {"hld-only", "code-verified", "discrepancy-found"}
VALID_MONITORS = {
    "not_implemented", "evolved_beyond_hld", "partially_implemented", "deprecated",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)

# g) non-ASCII control chars: C0/C1 except TAB(09), LF(0A), CR(0D)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
REPL_CHAR = "�"
# Classic UTF-8-misread-as-Latin-1 mojibake fragments. Conservative list: only
# patterns that essentially never occur in legitimate Japanese / English prose.
MOJIBAKE_RE = re.compile(
    r"(Ã[\x80-\xbf]|Â[\x80-\xbf]|â\x80[\x90-\xbf]|â\x82\xac)"
)


def parse_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return None, text
    fm_raw, body = m.group(1), m.group(2)
    if yaml is not None:
        try:
            data = yaml.safe_load(fm_raw) or {}
        except Exception as e:
            data = {"__parse_error__": str(e)}
    else:
        data = _simple_yaml(fm_raw)
    return data, body


def _simple_yaml(raw: str) -> dict:
    out: dict = {}
    for line in raw.splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    return out


def _cache_paths_check_enabled() -> bool:
    """Path liveness check runs when the cache exists, or when forced.

    On CI the cache is not provisioned so the check is silently skipped to avoid
    false positives. Set FRONTMATTER_LINT_CHECK_PATHS=1 to force-enable,
    FRONTMATTER_LINT_CHECK_PATHS=0 to force-disable.
    """
    flag = os.environ.get("FRONTMATTER_LINT_CHECK_PATHS")
    if flag == "1":
        return True
    if flag == "0":
        return False
    return CACHE_DIR.is_dir()


def lint_file(path: Path, *, check_paths: bool):
    """Return (hard_violations, warnings)."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return ([f"g: file is not valid UTF-8 ({e})"], [])

    fm, body = parse_frontmatter(text)
    violations: list[str] = []
    warnings: list[str] = []

    # g) mojibake / control chars (whole-file scan)
    m = CONTROL_RE.search(text)
    if m:
        violations.append(
            f"g: non-ASCII control char U+{ord(m.group()):04X} at offset {m.start()}"
        )
    if REPL_CHAR in text:
        violations.append("g: U+FFFD replacement character present")
    mb = MOJIBAKE_RE.search(text)
    if mb:
        violations.append(
            f"g: mojibake-like sequence {mb.group()!r} at offset {mb.start()}"
        )

    if fm is None:
        violations.append("missing frontmatter block")
        return violations, warnings
    if "__parse_error__" in fm:
        violations.append(
            f"f: YAML parse error: {fm['__parse_error__'].splitlines()[0]}"
        )
        return violations, warnings

    verification = fm.get("verification")
    title = fm.get("title")
    area = fm.get("area")
    last_verified = fm.get("last_verified")
    sources = fm.get("sources")

    # e) title / area
    if not title or not str(title).strip():
        violations.append("e: title is empty")
    if verification not in ("stub", "meta"):
        if not area:
            violations.append("e: area missing")
        elif area not in VALID_AREAS:
            violations.append(f"e: area '{area}' not in valid enum")

        # d) last_verified ISO date
        if not last_verified:
            violations.append("d: last_verified missing")
        else:
            s = str(last_verified).strip()
            if not DATE_RE.match(s):
                violations.append(f"d: last_verified '{s}' is not YYYY-MM-DD")
            else:
                try:
                    _dt.date.fromisoformat(s)
                except ValueError:
                    violations.append(f"d: last_verified '{s}' is not a valid date")

    # a) sources non-empty
    if verification in VERIFICATIONS_REQUIRING_SOURCES:
        if not sources or (isinstance(sources, list) and len(sources) == 0):
            violations.append(f"a: sources empty but verification={verification}")

    # b) code-verified must not have HLD-only admonition at top of body
    body_stripped = body.lstrip("\n")
    if verification == "code-verified":
        for line in body_stripped.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("!!! warning") and "HLD-only" in line:
                violations.append('b: code-verified page has HLD-only admonition')
            break

    # c) discrepancy-found must contain a 実装との乖離 section
    if verification == "discrepancy-found":
        if "実装との乖離" not in body and "実装からの乖離" not in body:
            violations.append("c: discrepancy-found page missing '実装との乖離' section")

    # f) monitor enum check and presence requirement for discrepancy-found
    monitor = fm.get("monitor")
    if monitor is not None and str(monitor).strip():
        mm = str(monitor).strip()
        if mm not in VALID_MONITORS:
            violations.append(f"f: monitor '{mm}' not in valid enum")
    elif verification == "discrepancy-found":
        violations.append("f: discrepancy-found page missing 'monitor' field")

    # i) description recommended (warn-only)
    description = fm.get("description")
    if description is None or not str(description).strip():
        warnings.append("i: description field missing (recommended for SEO; run gen_descriptions.py)")

    # h) sources[].path liveness check (warning bucket)
    if check_paths and isinstance(sources, list):
        for src in sources:
            if not isinstance(src, dict):
                continue
            repo = src.get("repo")
            spath = src.get("path")
            if not repo or not spath:
                continue
            repo_name = str(repo).split("/")[-1]
            repo_root = CACHE_DIR / repo_name
            if not repo_root.is_dir():
                # repo not cached locally (out-of-scope per repos.json); skip silently
                continue
            clean = str(spath).split("#")[0]
            full = repo_root / clean
            if not full.exists():
                warnings.append(f"h: source path not found in cache: {repo} {spath}")

    return violations, warnings


def main() -> int:
    md_files = sorted(DOCS_DIR.rglob("*.md"))
    check_paths = _cache_paths_check_enabled()
    hard: dict[Path, list[str]] = {}
    warn: dict[Path, list[str]] = {}
    for f in md_files:
        v, w = lint_file(f, check_paths=check_paths)
        if v:
            hard[f] = v
        if w:
            warn[f] = w

    # v1-compatible single report (hard violations only)
    lines = ["# Frontmatter Lint Report", ""]
    lines.append(f"- Scanned: {len(md_files)} files")
    lines.append(f"- Violations: {len(hard)} files")
    lines.append("")
    if not hard:
        lines.append("All checks pass.")
    else:
        lines.append("## Violations")
        lines.append("")
        for f, vs in sorted(hard.items()):
            rel = f.relative_to(REPO_ROOT)
            lines.append(f"### `{rel}`")
            for v in vs:
                lines.append(f"- {v}")
            lines.append("")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # v2 enhanced report
    v2 = ["# Frontmatter Lint Report (v2)", ""]
    v2.append(f"- Scanned: {len(md_files)} files")
    v2.append(f"- Hard violations: {len(hard)} files")
    v2.append(f"- Warnings (path liveness): {len(warn)} files")
    v2.append(
        f"- Path liveness check: {'enabled' if check_paths else 'skipped (no .cache/sonic-sources)'}"
    )
    v2.append("")
    if hard:
        v2.append("## Hard violations (fail build)")
        v2.append("")
        for f, vs in sorted(hard.items()):
            rel = f.relative_to(REPO_ROOT)
            v2.append(f"### `{rel}`")
            for v in vs:
                v2.append(f"- {v}")
            v2.append("")
    if warn:
        v2.append("## Warnings (do not fail build)")
        v2.append("")
        for f, ws in sorted(warn.items()):
            rel = f.relative_to(REPO_ROOT)
            v2.append(f"### `{rel}`")
            for w in ws:
                v2.append(f"- {w}")
            v2.append("")
    if not hard and not warn:
        v2.append("All checks pass.")
    REPORT_V2_PATH.write_text("\n".join(v2) + "\n", encoding="utf-8")

    print(
        f"scanned={len(md_files)} hard={len(hard)} warn={len(warn)} "
        f"path_check={'on' if check_paths else 'off'}"
    )
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
