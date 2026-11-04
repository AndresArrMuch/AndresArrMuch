#!/bin/bash
# uso: run.sh <db> [args del script]
DB=$1; shift
cd /tmp/claude-0/wt_af/backend
DATABASE_URL="postgresql://postgres@/$DB?host=/var/run/postgresql&port=5433" FLASK_ENV=development \
  /tmp/claude-0/venv/bin/python -W ignore /tmp/claude-0/wt_af/backend/scripts/anular_f030_000119_solo_sistema.py "$@" 2>&1 | grep -vE "^\s*$|WARNING|Warning|warn\("
echo "(codigo de salida ${PIPESTATUS[0]})"
