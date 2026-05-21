# RideList Infrastructure Generation Prompt

You are writing the Docker Compose 
configuration for the RideList test 
environment on EC2.

Target location:
- root of this directory

Create the following files:

- docker-compose.yml
- docker-compose.dev.yml
- .env.example
- scripts/start.sh
- scripts/inject-secrets.sh

Also prepare the following directory structure:

.
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── nginx/
│   └── nginx.conf
└── scripts/
    ├── start.sh
    └── inject-secrets.sh

Requirements:
- Use Docker Compose version 3.8
- Use PostgreSQL 15 Alpine
- Use AWS ECR images for backend/frontend in production
- Use nginx as reverse proxy
- Use internal Docker bridge networking
- Persist PostgreSQL data on host disk
- Add container healthchecks
- Add JSON file log rotation limits
- Use production-safe defaults
- Backend must not be publicly exposed directly
- nginx must expose ports 80 and 443
- Use AWS Secrets Manager for runtime secret injection
- Use `.env.backend` for backend secret injection
- Local development overrides must expose useful ports
- nginx should be optional locally

---

# docker-compose.yml

```yaml
version: "3.8"

services:

  postgres:
    image: postgres:15-alpine
    container_name: ridelist-postgres
    restart: always
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USERNAME}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - /data/postgres:/var/lib/postgresql/data
    networks:
      - internal
    healthcheck:
      test: [ "CMD-SHELL",
        "pg_isready -U ${DB_USERNAME} \
             -d ${DB_NAME}" ]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  backend:
    image: ${ECR_BACKEND_IMAGE}
    container_name: ridelist-backend
    restart: always
    env_file:
      - .env.backend
    environment:
      JAVA_OPTS: >-
        -Xmx350m -Xms256m
        -XX:+UseContainerSupport
        -Djava.security.egd=file:/dev/./urandom
      DB_HOST: postgres
      DB_PORT: "5432"
      DB_NAME: ${DB_NAME}
      DB_USERNAME: ${DB_USERNAME}
      DB_PASSWORD: ${DB_PASSWORD}
      SPRING_PROFILES_ACTIVE: prod
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - internal
    healthcheck:
      test: [ "CMD", "wget", "-q",
              "-O", "/dev/null",
              "http://localhost:8080/actuator/health" ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  frontend:
    image: ${ECR_FRONTEND_IMAGE}
    container_name: ridelist-frontend
    restart: always
    networks:
      - internal
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    container_name: ridelist-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - /var/www/certbot:/var/www/certbot:ro
    depends_on:
      backend:
        condition: service_healthy
      frontend:
        condition: service_started
    networks:
      - internal
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  internal:
    driver: bridge
```


# docker-compose.dev.yml

```yaml
version: "3.8"

services:

  postgres:
    ports:
      - "5432:5432"

  backend:
    image: ridelist-backend:local
    environment:
      SPRING_PROFILES_ACTIVE: dev
      JAVA_OPTS: "-Xmx512m -Xms256m"
    ports:
      - "8080:8080"

  frontend:
    image: ridelist-frontend:local
    ports:
      - "3000:80"

  nginx:
    profiles:
      - nginx-local

 ```

 # .env.example

 ```yaml
 # Docker Compose environment template
# Copy to .env.shared and fill in values
# NEVER commit .env.shared to git

# ECR Image URIs (set by CI/CD)
ECR_BACKEND_IMAGE=
ECR_FRONTEND_IMAGE=

# Database
DB_NAME=ridelist
DB_USERNAME=ridelist
DB_PASSWORD=

# These are also injected into .env.shared-dev.backend
# from AWS Secrets Manager
```

# scripts/start.sh
```bash
#!/bin/bash
set -e

echo "=== RideList Startup ==="
echo "Time: $(date)"

# 1. Inject secrets from AWS Secrets Manager
echo "Injecting secrets..."
bash /opt/ridelist/scripts/inject-secrets.sh

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
```

# scripts/inject-secrets.sh
```bash
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
    jq -r 'to_entries[] |
      "\(.key)=\(.value)"' >> $ENV_FILE
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
```

## AFTER EVERYTHING
Inspect the USAGE.md and confirm the correctness, then edit if need be and reformat in a proper markdown file

seed
INSERT INTO users (name, email)
VALUES ('Test User', 'test@example.com');