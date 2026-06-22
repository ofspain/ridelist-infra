#!/bin/bash

set -euo pipefail

# ==========================================================
# CONSTANTS
# ==========================================================

BASE_DIR="/opt/ridelist"

RUNTIME_FILE="$BASE_DIR/.env.runtime"

REQUIRED_FILE="$BASE_DIR/required-secrets.list"

OPTIONAL_FILE="$BASE_DIR/optional-secrets.list"

OUT_FILE="$BASE_DIR/.env"

# ==========================================================
# LOGGING
# ==========================================================

log() {
  echo "[INFO ] $1"
}

warn() {
  echo "[WARN ] $1"
}

error() {
  echo "[ERROR] $1"
}

# ==========================================================
# VALIDATION
# ==========================================================

[ -f "$RUNTIME_FILE" ] || {
  error "Missing runtime file: $RUNTIME_FILE"
  exit 1
}

[ -f "$REQUIRED_FILE" ] || {
  error "Missing required secrets file: $REQUIRED_FILE"
  exit 1
}

# ==========================================================
# LOAD ENVIRONMENT
# ==========================================================

source "$RUNTIME_FILE"

ENV="${ENVIRONMENT:-}"

if [ -z "$ENV" ]; then
  error "ENVIRONMENT not configured"
  exit 1
fi

log "======================================"
log "RideList Configuration Loader"
log "Environment: $ENV"
log "======================================"

# ==========================================================
# PREPARE ENV FILE
# ==========================================================

rm -f "$OUT_FILE"

touch "$OUT_FILE"

chmod 600 "$OUT_FILE"

# ==========================================================
# SECRET PROCESSOR
# ==========================================================

process_secret() {

  local SECRET_NAME="$1"

  local REQUIRED="$2"

  local SECRET_PATH="/ridelist/$ENV/$SECRET_NAME"

  log "Fetching: $SECRET_PATH"

  if ! SECRET_JSON=$(
      aws secretsmanager get-secret-value \
        --secret-id "$SECRET_PATH" \
        --query SecretString \
        --output text 2>/dev/null
    )
  then

      if [ "$REQUIRED" = "true" ]; then
          error "Required secret missing: $SECRET_PATH"
          exit 1
      fi

      warn "Optional secret missing: $SECRET_PATH"

      return
  fi

  if [ -z "$SECRET_JSON" ] || [ "$SECRET_JSON" = "null" ]; then

      if [ "$REQUIRED" = "true" ]; then
          error "Required secret empty: $SECRET_PATH"
          exit 1
      fi

      warn "Optional secret empty: $SECRET_PATH"

      return
  fi

  if ! echo "$SECRET_JSON" | jq -e . >/dev/null 2>&1
  then

      if [ "$REQUIRED" = "true" ]; then
          error "Invalid JSON in secret: $SECRET_PATH"
          exit 1
      fi

      warn "Invalid JSON in optional secret: $SECRET_PATH"

      return
  fi

  echo "$SECRET_JSON" \
    | jq -r 'to_entries[] | "\(.key)=\(.value)"' \
    >> "$OUT_FILE"

  echo "" >> "$OUT_FILE"
}

# ==========================================================
# DUPLICATE VALIDATION
# ==========================================================

TMP_FILE=$(mktemp)

cat "$REQUIRED_FILE" > "$TMP_FILE"

if [ -f "$OPTIONAL_FILE" ]; then
  cat "$OPTIONAL_FILE" >> "$TMP_FILE"
fi

DUPLICATES=$(
  grep -Ev '^\s*#|^\s*$' "$TMP_FILE" \
  | sort \
  | uniq -d
)

rm -f "$TMP_FILE"

if [ -n "$DUPLICATES" ]; then
  error "Duplicate secret definitions detected"

  echo "$DUPLICATES"

  exit 1
fi

# ==========================================================
# PROCESS REQUIRED SECRETS
# ==========================================================

log "Processing required secrets"

while IFS= read -r SECRET || [ -n "$SECRET" ]
do

  SECRET="$(echo "$SECRET" | xargs)"

  [ -z "$SECRET" ] && continue

  [[ "$SECRET" =~ ^# ]] && continue

  process_secret "$SECRET" "true"

done < "$REQUIRED_FILE"

# ==========================================================
# PROCESS OPTIONAL SECRETS
# ==========================================================

if [ -f "$OPTIONAL_FILE" ]; then

  log "Processing optional secrets"

  while IFS= read -r SECRET || [ -n "$SECRET" ]
  do

    SECRET="$(echo "$SECRET" | xargs)"

    [ -z "$SECRET" ] && continue

    [[ "$SECRET" =~ ^# ]] && continue

    process_secret "$SECRET" "false"

  done < "$OPTIONAL_FILE"

fi

# ==========================================================
# FINAL VALIDATION
# ==========================================================

if [ ! -s "$OUT_FILE" ]; then
  error "Generated .env file is empty"
  exit 1
fi

# ==========================================================
# SUMMARY
# ==========================================================

log "Generated: $OUT_FILE"

VARIABLE_COUNT=$(
  grep -cv '^$' "$OUT_FILE"
)

log "Variables loaded: $VARIABLE_COUNT"

log "Configuration loading completed successfully"