#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"

mkdir -p "$LOG_DIR"

python3 "$ROOT_DIR/scripts/update_jobs.py" >> "$LOG_DIR/update_jobs.log" 2>&1
