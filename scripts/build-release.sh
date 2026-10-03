#!/usr/bin/env bash
set -euo pipefail

SIGNING_DIR="${HOME}/.config/utilitaria-signing"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export UTILITARIA_KEYSTORE="${SIGNING_DIR}/utilitaria-upload.jks"
export UTILITARIA_KEYSTORE_PASSWORD="$(<"${SIGNING_DIR}/password")"
export UTILITARIA_API_URL="https://utilitaria-api.eav-labs.com"

FLUTTER_BIN="${FLUTTER_HOME:-/home/ernesto/flutter}/bin/flutter"
cd "${PROJECT_ROOT}/flutter_app"
exec "${FLUTTER_BIN}" build apk --release \
  --dart-define="API_BASE_URL=${UTILITARIA_API_URL}" \
  "$@"
