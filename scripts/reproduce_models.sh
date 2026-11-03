#!/usr/bin/env bash
# Re-creates the shipped models and every evaluation report from public data (CPU only).
set -euo pipefail
cd "$(dirname "$0")/.."
python datasets/scripts/prepare_usda_fruit_flower.py ${SRC:+--src "$SRC"}   # clones ~6 GB if SRC is not set
python ai-engine/training/train_detector.py
python ai-engine/training/evaluate_detector.py
python ai-engine/training/train_species.py
echo "Models in ai-engine/models, reports in ai-engine/reports"
