#!/usr/bin/env bash
# SENTINEL2 — Daily Pipeline Runner
# Usage:
#   ./run.sh                  # Full daily run (today)
#   ./run.sh --resume         # Resume from checkpoint
#   ./run.sh --date 2026-03-28
#   ./run.sh --step 10        # Single step
#   ./run.sh --seed           # Initialize DB + seed data only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment
if [ -f .env ]; then
    set -a; source .env; set +a
fi

# Check for seed-only mode
if [[ "${1:-}" == "--seed" ]]; then
    echo "[SENTINEL2] Running database seed..."
    python -c "
from src.db.connection import init_pool
from src.db.seed import run_schema, seed_all
init_pool()
run_schema()
seed_all()
print('Database seeded successfully.')
"
    exit 0
fi

# Create output directories
mkdir -p reports logs memory/agents

# Run pipeline
echo "[SENTINEL2] Starting pipeline..."
python -m src.pipeline "$@" 2>&1 | tee "logs/pipeline_$(date +%Y%m%d_%H%M%S).log"
echo "[SENTINEL2] Pipeline complete."
