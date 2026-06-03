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
  j) page_kind is optional; when present, must be in VALID_PAGE_KINDS
     ({chapter-index}). Chapter-index pages (22 章扉) are evaluated on a
     different quality-audit rubric (relaxed body-volume / per-claim
     verification requirements); this linter only enforces the enum value.
  k) related opt-out markers (`_no_related`, `_no_related_yang`,
     `_no_related_cli`, `_no_related_config_db`, legacy `_no_yang`):
     when present under `related:`, must be boolean `true`. These are
     recognized by find_empty_related.py / find_partial_empty_related.py /
     check_discrepancy_related.py to suppress empty-related warnings for
     reference-index / glossary / style-guide / meta pages. The linter
     itself only validates the marker type (warn-only).

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
except Exception as _yaml_exc:  # pragma: no cover
    # PyYAML is REQUIRED. The previous fallback parser (`_simple_yaml`) silently
    # mis-parsed list-form fields like `sources:` (it skipped indented lines),
    # which produced ~675 false-positive "a: sources empty" hard violations
    # whenever the linter was run with a stock python3 that lacked PyYAML.
    # That made the result indistinguishable from a real regression. Fail loudly
    # instead so the operator installs PyYAML (CI does: see `pip install PyYAML`
    # in .github/workflows/ci.yml; locally use `.venv/bin/python`).
    print(
        "frontmatter_lint: PyYAML is required. Install it with `pip install PyYAML` "
        "or run via `.venv/bin/python meta/scripts/frontmatter_lint.py`.\n"
        f"  (import error: {_yaml_exc})",
        file=sys.stderr,
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
CACHE_DIR = REPO_ROOT / ".cache" / "sonic-sources"
REPORT_PATH = REPO_ROOT / "meta" / "frontmatter-lint-report.md"
REPORT_V2_PATH = REPO_ROOT / "meta" / "frontmatter-lint-report-v2.md"

VALID_AREAS = {
    "routing", "switching", "overlay", "acl-qos", "system",
    "management", "platform", "architecture", "internals", "reference",
    "topics",
}
VALID_VERIFICATION = {
    "hld-only", "issue-confirmed", "code-verified", "discrepancy-found",
    "runbook-verified", "stub", "meta",
}
VERIFICATIONS_REQUIRING_SOURCES = {
    "hld-only", "code-verified", "discrepancy-found", "runbook-verified",
}
VALID_MONITORS = {
    "not_implemented", "evolved_beyond_hld", "partially_implemented", "deprecated",
}
# page_kind: optional tag distinguishing chapter index (gateway) pages from
# regular explanatory pages. Quality-audit round 14+ uses this to apply a
# different rubric to chapter indices (relaxed body-volume / per-claim
# verification requirements). The linter accepts it as optional and only
# validates the enum value when present.
VALID_PAGE_KINDS = {"chapter-index", "split-child", "split-hub"}
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
    try:
        data = yaml.safe_load(fm_raw) or {}
    except Exception as e:
        data = {"__parse_error__": str(e)}
    return data, body


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
    if verification is not None and str(verification).strip():
        vv = str(verification).strip()
        if vv not in VALID_VERIFICATION:
            violations.append(f"verification '{vv}' not in valid enum {sorted(VALID_VERIFICATION)}")
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

    # c) discrepancy-found must contain a 実装との乖離 section.
    # Exception: split-child pages delegate this section to the sibling
    # '-limitations.md' page (the split-hub keeps verification/sources but
    # the discrepancy detail lives in the limitations child).
    page_kind_val = str(fm.get("page_kind") or "").strip()
    if verification == "discrepancy-found" and page_kind_val != "split-child":
        # `!!! diff "HLD と実装の差分"` admonition (inject_diff_admonition.py)
        # で乖離節をラップした後も検出できるよう、admonition マーカー /
        # title 文字列 / 旧来の H2 見出しのいずれかが残っていれば OK とする。
        has_diff_section = (
            "実装との乖離" in body
            or "実装からの乖離" in body
            or "HLD と実装の差分" in body
            or "<!-- diff-admonition -->" in body
        )
        if not has_diff_section:
            violations.append("c: discrepancy-found page missing '実装との乖離' section")

    # f) monitor enum check and presence requirement for discrepancy-found
    monitor = fm.get("monitor")
    if monitor is not None and str(monitor).strip():
        mm = str(monitor).strip()
        if mm not in VALID_MONITORS:
            violations.append(f"f: monitor '{mm}' not in valid enum")
    elif verification == "discrepancy-found":
        violations.append("f: discrepancy-found page missing 'monitor' field")

    # page_kind enum check (optional field; only validate value if present).
    # Chapter-index pages are scored on a different rubric by quality-audit
    # round 14+: body-volume and per-claim verification axes are relaxed,
    # but frontmatter / link-coverage axes are still enforced here.
    page_kind = fm.get("page_kind")
    if page_kind is not None and str(page_kind).strip():
        pk = str(page_kind).strip()
        if pk not in VALID_PAGE_KINDS:
            violations.append(f"page_kind '{pk}' not in valid enum {sorted(VALID_PAGE_KINDS)}")

    # i) description required (warn-only) for regular content pages.
    # Excluded from the requirement:
    #   - page_kind in {chapter-index, split-hub, split-child}
    #     (gateway / navigational / fragment pages; their description is
    #     supplied by the hub or parent chapter)
    #   - verification in {meta, stub}
    #     (placeholder / index pages that have little body to summarise)
    # mkdocs-material consumes `description:` for the `<meta name="description">`
    # tag (SEO / SERP / OGP card layouts), so regular explanatory pages should
    # always carry one. Generate missing values with gen_descriptions.py.
    description = fm.get("description")
    pk_for_desc = str(fm.get("page_kind") or "").strip()
    ver_for_desc = str(fm.get("verification") or "").strip()
    desc_exempt = (
        pk_for_desc in {"chapter-index", "split-hub", "split-child"}
        or ver_for_desc in {"meta", "stub"}
    )
    if not desc_exempt and (description is None or not str(description).strip()):
        warnings.append("i: description field missing (required for SEO; run gen_descriptions.py)")

    # k) related opt-out markers must be boolean true when present.
    # Recognized markers (under `related:`):
    #   - _no_related            : opt out all three (cli / config_db / yang)
    #   - _no_related_yang       : opt out yang only
    #   - _no_related_cli        : opt out cli only
    #   - _no_related_config_db  : opt out config_db only
    #   - _no_yang               : legacy alias for _no_related_yang
    # The linter only checks the type; downstream lints
    # (find_empty_related.py / check_discrepancy_related.py /
    # find_partial_empty_related.py) consume them to suppress warnings.
    rel_block = fm.get("related")
    if isinstance(rel_block, dict):
        for marker in (
            "_no_related",
            "_no_related_yang",
            "_no_related_cli",
            "_no_related_config_db",
            "_no_yang",
        ):
            if marker in rel_block and rel_block[marker] is not True:
                warnings.append(
                    f"k: related.{marker} should be boolean `true` "
                    f"(got {rel_block[marker]!r})"
                )

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
