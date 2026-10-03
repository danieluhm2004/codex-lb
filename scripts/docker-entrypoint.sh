#!/bin/sh
set -eu

# Materialize secrets for platforms without volumes or secret files, e.g. Nitroship.
if [ -n "${CODEX_LB_ENCRYPTION_KEY:-}" ]; then
  if [ "${#CODEX_LB_ENCRYPTION_KEY}" -eq 43 ]; then
    CODEX_LB_ENCRYPTION_KEY="${CODEX_LB_ENCRYPTION_KEY}="
  fi
  export CODEX_LB_ENCRYPTION_KEY_FILE="${CODEX_LB_ENCRYPTION_KEY_FILE:-/var/lib/codex-lb/encryption.key}"
  (
    umask 077
    printf '%s' "$CODEX_LB_ENCRYPTION_KEY" > "$CODEX_LB_ENCRYPTION_KEY_FILE"
    chmod 600 "$CODEX_LB_ENCRYPTION_KEY_FILE"
  )
  unset CODEX_LB_ENCRYPTION_KEY
fi

if [ "${CODEX_LB_DATABASE_MIGRATE_ON_STARTUP:-true}" = "true" ]; then
  python -m app.db.migrate upgrade
fi

# Disable app-level startup migration so app/db/session.py init_db() does not
# run migrations again inside the app process.
export CODEX_LB_DATABASE_MIGRATE_ON_STARTUP=false

exec python -m app.cli --host 0.0.0.0 --port 2455
