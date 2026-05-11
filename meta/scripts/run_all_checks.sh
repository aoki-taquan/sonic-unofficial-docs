#!/usr/bin/env bash
# Run all generator scripts in --check mode (drift detection).
#
# Usage:
#   bash meta/scripts/run_all_checks.sh
#
# Equivalent to the drift checks run in CI. If any generator detects that its
# derived artifact is out of sync with the source-of-truth (frontmatter /
# meta/index/*), the corresponding script exits non-zero and this wrapper
# aborts. Run `bash meta/scripts/run_all_generators.sh` to regenerate.
set -e
cd "$(dirname "$0")/../.."

python3 meta/scripts/gen_coverage.py --check
python3 meta/scripts/gen_cross_ref.py --check
python3 meta/scripts/gen_discrepancy_index.py --check
python3 meta/scripts/gen_index_banner.py --check
python3 meta/scripts/gen_glossary_xref.py --check
python3 meta/scripts/gen_cdb_mermaid.py --check
python3 meta/scripts/gen_cli_mermaid.py --check
python3 meta/scripts/gen_yang_mermaid.py --check
python3 meta/scripts/render_evidence.py --check

echo "All drift checks passed."
