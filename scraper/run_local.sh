#!/usr/bin/env bash
# Run the scraper locally and push the refreshed data to GitHub.
# Usage: ./scraper/run_local.sh
set -euo pipefail

# cd to the repo root (the directory that contains this script's parent).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "→ Running scraper…"
( cd scraper && python scrape.py )

echo "→ Committing data/data.json…"
git add data/data.json
if git diff --staged --quiet; then
  echo "  (no changes — nothing to push)"
  exit 0
fi

git commit -m "chore: update apartment data $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "→ Pushing to origin/main…"
git push origin main

echo "✓ Done."
