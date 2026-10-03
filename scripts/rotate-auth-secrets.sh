#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/backend/.env"
SECRETS_DIR="${HOME}/.config/utilitaria-auth"
SECRETS_FILE="${SECRETS_DIR}/enrollment-codes"

mkdir -p "${SECRETS_DIR}"
chmod 700 "${SECRETS_DIR}"

ADMIN_CODE="$(openssl rand -hex 12)"
MEMBER_CODE="$(openssl rand -hex 12)"
CAPTURE_CODE="$(openssl rand -hex 12)"
SERVICE_TOKEN="$(openssl rand -base64 48 | tr -d '\n')"
LEGACY_KEY="$(openssl rand -base64 48 | tr -d '\n')"

upsert() {
  local key="$1"
  local value="$2"
  local temporary
  temporary="$(mktemp "${ENV_FILE}.XXXXXX")"
  awk -v key="${key}" -v value="${value}" '
    BEGIN { found = 0 }
    index($0, key "=") == 1 { print key "=" value; found = 1; next }
    { print }
    END { if (!found) print key "=" value }
  ' "${ENV_FILE}" > "${temporary}"
  chmod --reference="${ENV_FILE}" "${temporary}"
  mv "${temporary}" "${ENV_FILE}"
}

upsert API_KEY "${LEGACY_KEY}"
upsert ALLOW_LEGACY_API_KEY "false"
upsert ADMIN_ENROLLMENT_CODE "${ADMIN_CODE}"
upsert MEMBER_ENROLLMENT_CODE "${MEMBER_CODE}"
upsert CAPTURE_ENROLLMENT_CODE "${CAPTURE_CODE}"
upsert SERVICE_API_TOKEN "${SERVICE_TOKEN}"

umask 077
{
  echo "ADMIN_ENROLLMENT_CODE=${ADMIN_CODE}"
  echo "MEMBER_ENROLLMENT_CODE=${MEMBER_CODE}"
  echo "CAPTURE_ENROLLMENT_CODE=${CAPTURE_CODE}"
} > "${SECRETS_FILE}"

echo "Credenciales rotadas. Códigos guardados en ${SECRETS_FILE}"
