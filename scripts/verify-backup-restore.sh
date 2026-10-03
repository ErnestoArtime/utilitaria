#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Uso: $0 /ruta/al/backup.dump" >&2
  exit 2
fi

BACKUP_FILE="$1"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_USER="$(awk -F= '$1 == "POSTGRES_USER" {print substr($0, index($0, "=") + 1)}' "${PROJECT_ROOT}/backend/.env")"
VERIFY_DB="utilitaria_restore_check_$(date +%s)"

cleanup() {
  docker exec backend-db-1 dropdb --if-exists -U "${DB_USER}" "${VERIFY_DB}" >/dev/null 2>&1 || true
  docker exec backend-db-1 rm -f /tmp/utilitaria-restore-check.dump >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker cp "${BACKUP_FILE}" backend-db-1:/tmp/utilitaria-restore-check.dump
docker exec backend-db-1 createdb -U "${DB_USER}" "${VERIFY_DB}"
docker exec backend-db-1 pg_restore -U "${DB_USER}" -d "${VERIFY_DB}" --no-owner /tmp/utilitaria-restore-check.dump
docker exec backend-db-1 psql -U "${DB_USER}" -d "${VERIFY_DB}" -v ON_ERROR_STOP=1 -c "SELECT COUNT(*) FROM balance_entries;"
echo "Restauración temporal verificada correctamente."
