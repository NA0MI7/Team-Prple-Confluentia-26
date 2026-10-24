#!/bin/bash
# Collect baseline gate check results.
# Usage: ./scripts/collect_baseline.sh [SEED]

set -euo pipefail

SEED="${1:-0}"

echo "Running baseline gate checks with SEED=$SEED..."

MODE=baselines SEED="$SEED" docker compose up --build --abort-on-container-exit --exit-code-from harness

# Find the most recent run directory
RUN_DIR=$(ls -td logs/*/ 2>/dev/null | head -1)

if [ -z "$RUN_DIR" ]; then
    echo "ERROR: No log directory found"
    exit 1
fi

GATE_FILE="$RUN_DIR/gate.json"

if [ ! -f "$GATE_FILE" ]; then
    echo "ERROR: gate.json not found in $RUN_DIR"
    exit 1
fi

# Copy to baseline-results/
mkdir -p baseline-results
cp "$GATE_FILE" "baseline-results/gate.json"
cp "$GATE_FILE" "baseline-results/gate_seed${SEED}.json"

echo ""
echo "Gate results copied to baseline-results/gate.json (and gate_seed${SEED}.json)"
echo "Contents:"
cat "$GATE_FILE"
