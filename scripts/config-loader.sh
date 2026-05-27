#!/bin/bash
set -euo pipefail

ENV=${ENVIRONMENT:-test}
BASE_DIR="/opt/ridelist"
OUT_FILE="$BASE_DIR/.env"

echo "Loading configuration for: $ENV"

# Ensure output file is clean
> "$OUT_FILE"

# List of secrets (single source of truth)
SECRETS=(
  "database"
  "jwt"
  "app-config"
  "smtp"
  "aws"
  "ecr-images"
)

for SECRET in "${SECRETS[@]}"; do

  echo "Fetching $SECRET..."

  VALUE=$(aws secretsmanager get-secret-value \
    --secret-id "/ridelist/$ENV/$SECRET" \
    --query SecretString \
    --output text)

  # Convert JSON → ENV format
  echo "$VALUE" | jq -r 'to_entries[] | "\(.key)=\(.value)"' >> "$OUT_FILE"

done

# Lock file
chmod 600 "$OUT_FILE"

echo "Config written to $OUT_FILE"