#!/usr/bin/env python3
"""Frontmatter linter for docs/**/*.md.

Checks:
  a) verification in {hld-only, code-verified, discrepancy-found} -> sources non-empty
  b) verification == code-verified -> body does not start with '!!! warning "HLD-only"' admonition
  c) verification == discrepancy-found -> body contains a "実装との乖離" section
  d) last_verified matches YYYY-MM-DD
  e) title non-empty, area is a known enum
  f) monitor in {not_implemented, evolved_beyond_hld, partially_implemented, deprecated};
     verification == discrepancy-found -> monitor field must be present

Output: meta/frontmatter-lint-report.md
Exit code: 1 if any violations, else 0.
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # fallback simple parser below

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
REPORT_PATH = REPO_ROOT / "meta" / "frontmatter-lint-report.md"

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


def lint_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    violations: list[str] = []
    if fm is None:
        violations.append("missing frontmatter block")
        return violations
    if "__parse_error__" in fm:
        violations.append(f"f: YAML parse error: {fm['__parse_error__'].splitlines()[0]}")
        return violations

    verification = fm.get("verification")
    title = fm.get("title")
    area = fm.get("area")
    last_verified = fm.get("last_verified")
    sources = fm.get("sources")

    # e) title / area
    if not title or not str(title).strip():
        violations.append("e: title is empty")
    # skip area check for stub/meta pages
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
        # find first admonition line
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
        m = str(monitor).strip()
        if m not in VALID_MONITORS:
            violations.append(f"f: monitor '{m}' not in valid enum")
    elif verification == "discrepancy-found":
        violations.append("f: discrepancy-found page missing 'monitor' field")

    return violations


def main() -> int:
    md_files = sorted(DOCS_DIR.rglob("*.md"))
    results: dict[Path, list[str]] = {}
    for f in md_files:
        v = lint_file(f)
        if v:
            results[f] = v

    # write report
    lines = ["# Frontmatter Lint Report", ""]
    lines.append(f"- Scanned: {len(md_files)} files")
    lines.append(f"- Violations: {len(results)} files")
    lines.append("")
    if not results:
        lines.append("All checks pass.")
    else:
        lines.append("## Violations")
        lines.append("")
        for f, vs in sorted(results.items()):
            rel = f.relative_to(REPO_ROOT)
            lines.append(f"### `{rel}`")
            for v in vs:
                lines.append(f"- {v}")
            lines.append("")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"scanned={len(md_files)} violations={len(results)}")
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
