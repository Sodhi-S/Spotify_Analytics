#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH=backend:scripts
python3 scripts/run_ingest_once.py
