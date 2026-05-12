#!/usr/bin/env bash
# Run all generator / inject / aggregator scripts in sequence.
#
# Usage:
#   bash meta/scripts/run_all_generators.sh
#
# Pipeline order:
#   1. Index-class generators (mermaid embeds, glossary xref, cross-ref)
#   2. Inject-class transformers (yang xref/sibling, cli sibling, glossary links)
#   3. Aggregate-class generators (coverage, discrepancy, banner, changelog,
#      sitemap, snapshot, chapter-progress, next-reads, evidence, chapter-index)
#
# Run after frontmatter or meta/index updates to refresh all derived docs.
set -e
cd "$(dirname "$0")/../.."

# --- 1. Index-class (source-of-truth -> derived index/mermaid) ---
python3 meta/scripts/gen_cdb_mermaid.py
python3 meta/scripts/gen_cli_mermaid.py
python3 meta/scripts/gen_yang_mermaid.py
python3 meta/scripts/gen_glossary_xref.py
python3 meta/scripts/gen_cross_ref.py

# --- 2. Inject-class (rewrite page bodies with sibling/xref blocks) ---
# NOTE: inject_glossary_links runs LAST after gen_next_reads, because next-reads
# blocks include "HLD" text that glossary-links wraps in [HLD](glossary#...)
# anchors. If glossary-links ran first, gen_next_reads would strip those links.
python3 meta/scripts/inject_yang_xref.py
python3 meta/scripts/inject_yang_sibling.py
python3 meta/scripts/inject_cli_sibling.py

# --- 3. Aggregate-class (derived indexes / banners / progress) ---
python3 meta/scripts/enrich_chapter_index_related.py
python3 meta/scripts/gen_coverage.py
python3 meta/scripts/gen_discrepancy_index.py
python3 meta/scripts/gen_index_banner.py
python3 meta/scripts/gen_changelog.py
python3 meta/scripts/gen_chapter_progress.py
python3 meta/scripts/gen_next_reads.py
python3 meta/scripts/render_evidence.py

# Final pass: glossary inline-link injection (must follow gen_next_reads).
python3 meta/scripts/inject_glossary_links.py

# Sitemap and snapshot last: they harvest page descriptions which may include
# glossary anchors injected above. Running them earlier causes re-check drift.
python3 meta/scripts/gen_snapshot.py
python3 meta/scripts/gen_sitemap.py

# Disk-saving cleanup: drop any mkdocs build artifact left in the worktree so
# parallel agents do not accumulate hundreds of MB of duplicated site/ output.
rm -rf site/ 2>/dev/null || true

echo "All generators ran successfully."
