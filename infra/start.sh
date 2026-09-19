#!/bin/bash
set -euo pipefail
export XDG_CACHE_HOME=/tmp/cache
export XDG_CONFIG_HOME=/tmp/config
export DATABASE_PATH=/tmp/proofpact.sqlite3
export EVIDENCE_PATH=/tmp/evidence
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT
HOSTNAME=0.0.0.0 PORT=8080 node server.js
