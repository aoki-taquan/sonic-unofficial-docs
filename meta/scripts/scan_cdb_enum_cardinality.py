#!/usr/bin/env python3
"""
Scan each docs/reference/config-db/<slug>.md page for the cardinality of its
YANG-declared enum/pattern-alternative fields, and bucket pages into tiers:

  tier_high (>=15 distinct values in any leaf)
  tier_mid  (6..14)
  tier_low  (<6 or no enum-typed leaf detected)

Pages in the higher tiers need smaller agent batch sizes so that value-by-value
behavior analysis is not diluted. Output goes to
meta/cdb-enum-cardinality.json (machine-readable) for downstream agent
dispatchers and meta/cdb-enum-cardinality.md (human-readable summary).

YANG file resolution order:
  1. sonic-buildimage/src/sonic-yang-models/yang-models/sonic-<slug>.yang
     (also with hyphens/underscores swapped)
  2. sonic-mgmt-common/models/yang/sonic/sonic-<slug>.yang
  3. Fallback: any *.yang under either dir that declares
     `container <SLUG_UPPER>`.

The script is content-only: it does not require Python YAML, only re/pathlib.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
YANG_DIRS = [
    ROOT / '.cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models',
    ROOT / '.cache/sonic-sources/sonic-mgmt-common/models/yang/sonic',
]
CDB_DIR = ROOT / 'docs/reference/config-db'
OUT_JSON = ROOT / 'meta/cdb-enum-cardinality.json'
OUT_MD = ROOT / 'meta/cdb-enum-cardinality.md'

TIER_HIGH = 15  # >= this many values in any leaf
TIER_MID = 6    # >= this many values in any leaf


def parse_yang_leaves(path: Path) -> dict[str, list[str]]:
    """Return mapping of leaf-name -> list of distinct enum/pattern values."""
    try:
        text = path.read_text(errors='replace')
    except Exception:
        return {}
    fields: dict[str, list[str]] = {}
    pos = 0
    while True:
        m = re.search(r'\bleaf\s+(\S+?)\s*\{', text[pos:])
        if not m:
            break
        name = m.group(1).strip('"')
        start = pos + m.end() - 1  # opening brace
        depth = 1
        i = start + 1
        while i < len(text) and depth:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        body = text[start + 1:i - 1]
        pos = i

        values = re.findall(r'\benum\s+"?([^";\s]+)"?', body)
        if not values:
            pm = re.search(r'pattern\s+"([^"]+)"', body)
            if pm:
                pat = pm.group(1)
                if '|' in pat:
                    parts = [p.strip() for p in pat.split('|')]
                    if (all(re.fullmatch(r'[A-Za-z0-9_\-\.\(\)\s]+', p) for p in parts)
                            and len(parts) > 1):
                        values = parts
        if len(values) >= 2:
            seen: list[str] = []
            for v in values:
                if v not in seen:
                    seen.append(v)
            fields[name] = seen
    return fields


def find_yang(slug: str) -> Path | None:
    base = slug.replace('_', '-').lower()
    cands = [
        f'sonic-{base}.yang',
        f'sonic-{slug}.yang',
        f'sonic-{base.replace("-", "_")}.yang',
        f'sonic-{slug.replace("-", "_")}.yang',
    ]
    for d in YANG_DIRS:
        for c in cands:
            p = d / c
            if p.exists():
                return p
    upper = slug.replace('-', '_').upper()
    needle = f'container {upper}'
    for d in YANG_DIRS:
        for yp in d.glob('*.yang'):
            try:
                if needle in yp.read_text(errors='replace'):
                    return yp
            except Exception:
                continue
    return None


def main() -> int:
    if not CDB_DIR.exists():
        print(f'config-db dir not found: {CDB_DIR}', file=sys.stderr)
        return 2

    result: list[dict] = []
    for md in sorted(CDB_DIR.glob('*.md')):
        if md.name == 'index.md':
            continue
        slug = md.stem
        yp = find_yang(slug)
        fields = parse_yang_leaves(yp) if yp else {}
        max_card = max((len(v) for v in fields.values()), default=0)
        if max_card >= TIER_HIGH:
            tier = 'high'
        elif max_card >= TIER_MID:
            tier = 'mid'
        else:
            tier = 'low'
        result.append({
            'slug': slug,
            'yang': yp.name if yp else None,
            'yang_dir': str(yp.parent.relative_to(ROOT)) if yp else None,
            'max_card': max_card,
            'tier': tier,
            'enum_fields': {k: len(v) for k, v in fields.items()},
            'values': {k: v for k, v in fields.items()},
        })

    high = [r for r in result if r['tier'] == 'high']
    mid = [r for r in result if r['tier'] == 'mid']
    low = [r for r in result if r['tier'] == 'low']

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        'tier_thresholds': {'high': TIER_HIGH, 'mid': TIER_MID},
        'tier_high': high,
        'tier_mid': mid,
        'tier_low': low,
        'recommended_batch_sizes': {'high': 1, 'mid': 3, 'low': 12},
    }, indent=2, ensure_ascii=False))

    lines = [
        '# CDB enum cardinality report',
        '',
        '本ファイルは `meta/scripts/scan_cdb_enum_cardinality.py` の出力。',
        '高カーディナリティ enum を持つ CDB ページは値別深掘りで dilution されるので、',
        '値別解析バッチを以下のサイズに分けると過学習なく汎用に深さを揃えられる。',
        '',
        '| tier | 閾値 | 推奨 batch サイズ |',
        '|---|---|---|',
        f'| high | enum 値 ≥ {TIER_HIGH} | 1 page / agent |',
        f'| mid | {TIER_MID} ≤ values < {TIER_HIGH} | 3 pages / agent |',
        f'| low | values < {TIER_MID} | 12 pages / agent |',
        '',
        f'## high tier ({len(high)})',
        '',
    ]
    for r in high:
        flds = ', '.join(f'`{k}`={v}' for k, v in r['enum_fields'].items())
        lines.append(f'- `{r["slug"]}` — max={r["max_card"]} — fields: {flds}')
    lines += ['', f'## mid tier ({len(mid)})', '']
    for r in mid:
        flds = ', '.join(f'`{k}`={v}' for k, v in r['enum_fields'].items())
        lines.append(f'- `{r["slug"]}` — max={r["max_card"]} — fields: {flds}')
    lines += ['', f'## low tier ({len(low)})', '',
              'low tier は通常の 12 ページ/agent で十分。詳細は JSON 参照。']
    OUT_MD.write_text('\n'.join(lines) + '\n')

    print(f'high tier ({len(high)} pages):')
    for r in high:
        print(f'  {r["slug"]} max={r["max_card"]}')
    print(f'mid tier ({len(mid)} pages):')
    for r in mid:
        print(f'  {r["slug"]} max={r["max_card"]}')
    print(f'low tier: {len(low)} pages')
    print(f'wrote {OUT_JSON.relative_to(ROOT)}')
    print(f'wrote {OUT_MD.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
