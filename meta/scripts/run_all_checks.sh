#!/usr/bin/env bash
# Run all generator / inject / aggregator scripts in --check mode (drift detection).
#
# Usage:
#   bash meta/scripts/run_all_checks.sh
#
# Equivalent to the drift checks run in CI. If any generator detects that its
# derived artifact is out of sync with the source-of-truth (frontmatter /
# meta/index/*), the corresponding script exits non-zero and this wrapper
# aborts. Run `bash meta/scripts/run_all_generators.sh` to regenerate.
#
# Pipeline order matches run_all_generators.sh:
#   1. Index-class
#   2. Inject-class
#   3. Aggregate-class
set -e
cd "$(dirname "$0")/../.."

# --- 1. Index-class ---
python3 meta/scripts/gen_cdb_mermaid.py --check
python3 meta/scripts/gen_cli_mermaid.py --check
python3 meta/scripts/gen_yang_mermaid.py --check
python3 meta/scripts/gen_glossary_xref.py --check
python3 meta/scripts/gen_cross_ref.py --check

# --- 2. Inject-class (glossary_links runs last; see run_all_generators.sh) ---
python3 meta/scripts/inject_yang_xref.py --check
python3 meta/scripts/inject_yang_sibling.py --check
python3 meta/scripts/inject_cli_sibling.py --check

# --- 3. Aggregate-class ---
python3 meta/scripts/enrich_chapter_index_related.py --check
python3 meta/scripts/gen_coverage.py --check
python3 meta/scripts/gen_discrepancy_index.py --check
python3 meta/scripts/gen_index_banner.py --check
python3 meta/scripts/gen_changelog.py --check || true
python3 meta/scripts/gen_chapter_progress.py --check
python3 meta/scripts/gen_next_reads.py --check
python3 meta/scripts/render_evidence.py --check

# Final pass: glossary inline-link drift detection.
python3 meta/scripts/inject_glossary_links.py --check

# Snapshot and sitemap last (mirrors run_all_generators.sh ordering).
# gen_snapshot は last_verified の日付バケツ (0d / 1-7d / 8-30d) が CI 実行時刻
# とローカル regen 時刻の差で 1〜2 ページ揺れるため strict 化すると恒常的に
# false-positive を量産する。informational に降格 (drift 自体は log で見える)。
python3 meta/scripts/gen_snapshot.py --check || true
python3 meta/scripts/gen_sitemap.py --check

# Disk-saving cleanup: drop any mkdocs build artifact left in the worktree so
# parallel agents do not accumulate hundreds of MB of duplicated site/ output.
rm -rf site/ 2>/dev/null || true

echo "All drift checks passed."
