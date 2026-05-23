#!/bin/bash
set -e

echo "=== RideList Startup ==="
echo "Time: $(date)"

# 1. Inject secrets from AWS Secrets Manager
echo "Injecting secrets..."
bash /opt/ridelist/scripts/config-loader.sh

# 2. Authenticate Docker to ECR
echo "Authenticating to ECR..."
aws ecr get-login-password \
  --region eu-west-1 \
  --profile ridelist-cdk | \
  docker login --username AWS \
  --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.eu-west-1.amazonaws.com

# 3. Pull latest images
echo "Pulling latest images..."
docker compose pull

# 4. Start services
echo "Starting services..."
docker compose up -d

# 5. Wait for backend health
echo "Waiting for backend health..."

RETRIES=0
MAX_RETRIES=12

until docker compose exec -T backend \
  wget -q -O /dev/null \
  http://localhost:8080/actuator/health \
  2>/dev/null; do

  RETRIES=$((RETRIES+1))

  if [ $RETRIES -ge $MAX_RETRIES ]; then
    echo "Backend failed to become healthy"
    docker compose logs backend --tail=50
    exit 1
  fi

  echo "Waiting... ($RETRIES/$MAX_RETRIES)"
  sleep 10
done

echo "=== RideList is UP ==="
echo "Frontend: https://ofspain.click"
echo "API:      https://api.ofspain.click"
echo "Health:   https://api.ofspain.click/actuator/health"
