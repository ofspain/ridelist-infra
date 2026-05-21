#!/bin/bash
set -e

ENV_FILE="/opt/ridelist/.env.backend"
REGION="eu-west-1"
PROFILE="ridelist-cdk"

# Clear existing env file
> $ENV_FILE

echo "Fetching secrets from AWS Secrets Manager..."

fetch_secret() {
  local secret_id=$1

  aws secretsmanager get-secret-value \
    --secret-id "$secret_id" \
    --region $REGION \
    --profile $PROFILE \
    --query SecretString \
    --output text | \
    jq -r 'to_entries[] | "\(.key)=\(.value)"' >> $ENV_FILE
}

fetch_secret "/ridelist/test/database"
fetch_secret "/ridelist/test/jwt"
fetch_secret "/ridelist/test/aws"
fetch_secret "/ridelist/test/email"
fetch_secret "/ridelist/test/app"

# Secure the file
chmod 600 $ENV_FILE

echo "Secrets injected to $ENV_FILE"
echo "Total variables: $(wc -l < $ENV_FILE)"
