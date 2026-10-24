#!/usr/bin/env bash
# SessionStart hook: in a Claude Code cloud session (no Docker), install and start a local Postgres
# with pgvector on port 5433, the address the tests expect, and install the Python packages.
# On a laptop it does nothing: there, `make db` starts the same database in Docker.
set -euo pipefail

[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

uv sync --locked --quiet

if pg_isready -h 127.0.0.1 -p 5433 -q 2>/dev/null; then
  exit 0  # already running (the hook also runs when a session resumes)
fi

PG_BIN=$(ls -d /usr/lib/postgresql/*/bin | sort -V | tail -1)
PG_MAJOR=$(basename "$(dirname "$PG_BIN")")
if [ ! -f "/usr/share/postgresql/$PG_MAJOR/extension/vector.control" ]; then
  apt-get update -qq && apt-get install -y -qq "postgresql-$PG_MAJOR-pgvector" >/dev/null
fi

DATA=/tmp/helpdesk-pg
if [ ! -d "$DATA/data" ]; then
  mkdir -p "$DATA" && chown postgres "$DATA"
  su postgres -c "$PG_BIN/initdb -D $DATA/data -A trust" >/dev/null
fi
su postgres -c "$PG_BIN/pg_ctl -D $DATA/data -o '-p 5433 -k $DATA' -l $DATA/log -w start" >/dev/null

# Same user, password and database as compose.yaml (local-only, never a real secret).
psql -h 127.0.0.1 -p 5433 -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='helpdesk'" | grep -q 1 \
  || psql -h 127.0.0.1 -p 5433 -U postgres -qc "CREATE ROLE helpdesk LOGIN SUPERUSER PASSWORD 'local-only'"
psql -h 127.0.0.1 -p 5433 -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='helpdesk'" | grep -q 1 \
  || psql -h 127.0.0.1 -p 5433 -U postgres -qc "CREATE DATABASE helpdesk OWNER helpdesk"
echo "Postgres $PG_MAJOR + pgvector is running on 127.0.0.1:5433"
