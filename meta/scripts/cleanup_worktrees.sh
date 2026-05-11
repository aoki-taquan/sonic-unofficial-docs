#!/usr/bin/env bash
# Cleanup transient build / cache artifacts under all git worktrees.
#
# Usage:
#   bash meta/scripts/cleanup_worktrees.sh
#
# Removes per-worktree mkdocs `site/` output, Python `__pycache__/`, and
# pytest `.pytest_cache/` directories that accumulate when many parallel
# agents build the docs in their own worktree. Each of these can grow to
# hundreds of MB across a dozen worktrees and is fully reproducible from
# source, so it is safe to drop unconditionally.
#
# The script walks every working tree reported by `git worktree list`
# (including the main checkout) and deletes the artifacts in place. It is
# idempotent and never errors when a target directory is missing.
set -e
cd "$(dirname "$0")/../.."

REPO_ROOT="$(pwd)"
echo "[cleanup_worktrees] repo root = $REPO_ROOT"

# Collect worktree paths. `git worktree list --porcelain` lines look like
# `worktree /abs/path` followed by HEAD/branch lines, so grep the first.
WORKTREES=$(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2}')

if [ -z "$WORKTREES" ]; then
  # Fallback: just clean the current repo.
  WORKTREES="$REPO_ROOT"
fi

TOTAL=0
for wt in $WORKTREES; do
  if [ ! -d "$wt" ]; then
    continue
  fi
  echo "[cleanup_worktrees] cleaning $wt"

  # mkdocs build output
  if [ -d "$wt/site" ]; then
    rm -rf "$wt/site" 2>/dev/null || true
    TOTAL=$((TOTAL + 1))
  fi

  # Python bytecode caches anywhere in the tree
  find "$wt" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

  # pytest cache
  if [ -d "$wt/.pytest_cache" ]; then
    rm -rf "$wt/.pytest_cache" 2>/dev/null || true
  fi
  find "$wt" -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
done

echo "[cleanup_worktrees] done (site/ removed in $TOTAL worktrees)"
