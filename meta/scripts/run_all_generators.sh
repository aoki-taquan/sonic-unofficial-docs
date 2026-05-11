#!/usr/bin/env bash
# Run all generator scripts in sequence.
#
# Usage:
#   bash meta/scripts/run_all_generators.sh
#
# Each gen_*.py / render_*.py writes its derived artifact (coverage page,
# cross-ref index, discrepancy index, index banner, glossary x-ref, mermaid
# embeds for CDB / CLI / YANG, evidence panels). Run after frontmatter or
# meta/index updates to refresh all derived docs in one shot.
set -e
cd "$(dirname "$0")/../.."

python3 meta/scripts/gen_coverage.py
python3 meta/scripts/gen_cross_ref.py
python3 meta/scripts/gen_discrepancy_index.py
python3 meta/scripts/gen_index_banner.py
python3 meta/scripts/gen_glossary_xref.py
python3 meta/scripts/gen_cdb_mermaid.py
python3 meta/scripts/gen_cli_mermaid.py
python3 meta/scripts/gen_yang_mermaid.py
python3 meta/scripts/render_evidence.py

echo "All generators ran successfully."
