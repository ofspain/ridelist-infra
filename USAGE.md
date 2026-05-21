# RideList Infrastructure

This repository contains the Docker Compose infrastructure for the RideList EC2 test environment.

---

## Repository Structure

```text
.
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── nginx/
│   └── nginx.conf
└── scripts/
    ├── start.sh
    └── inject-secrets.sh
```

---

## Prerequisites

Install the following tools:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- [jq](https://stedolan.github.io/jq/download/)

Verify installations:

```bash
docker --version
docker compose version
aws --version
jq --version
```

---

## Environment Setup

Copy the environment template:

```bash
cp .env.shared.example .env.shared
```

Fill in the required values:

```env
DB_PASSWORD=your-password
ECR_BACKEND_IMAGE=your-backend-image-uri
ECR_FRONTEND_IMAGE=your-frontend-image-uri
```

> **Never** commit `.env` or `.env.backend` to git.

---

## Local Development

Run the stack locally using both compose files:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  up --build
```

This exposes:

| Service    | Address               |
|------------|-----------------------|
| PostgreSQL | `localhost:5432`      |
| Backend    | `localhost:8080`      |
| Frontend   | `localhost:3000`      |

> nginx is disabled by default in local development.

---

## Verify Services

Check running containers:

```bash
docker compose ps
```

All services should eventually show `healthy` or `running` status.

---

## View Logs

**Backend:**

```bash
docker compose logs backend --tail=20
```

**PostgreSQL:**

```bash
docker compose logs postgres --tail=10
```

**nginx:**

```bash
docker compose logs nginx --tail=10
```

---

## Test Internal Networking

Verify the backend can reach PostgreSQL:

```bash
docker compose exec backend \
  wget -q -O- \
  http://postgres:5432
```

Expected: PostgreSQL readiness output.

---

## Shut Down Services

Stop containers cleanly:

```bash
docker compose down
```

---

## Production Startup (EC2)

Run the startup script:

```bash
bash scripts/start.sh
```

The script will:

1. Fetch secrets from AWS Secrets Manager
2. Generate `.env.backend`
3. Authenticate Docker to AWS ECR
4. Pull latest images
5. Start all services
6. Wait for backend health checks

---

## AWS Secrets Manager

Secrets are loaded dynamically at startup from the following paths:

| Secret Path                  | Purpose           |
|------------------------------|-------------------|
| `/ridelist/test/database`    | Database credentials |
| `/ridelist/test/jwt`         | JWT signing key   |
| `/ridelist/test/aws`         | AWS credentials   |
| `/ridelist/test/email`       | Email config      |
| `/ridelist/test/app`         | App config        |

These are written to `.env.backend` at runtime.

---

## Security Notes

- Never commit `.env`
- Never commit `.env.backend`
- The backend is intentionally **not** publicly exposed
- nginx is the **only** public entry point
- PostgreSQL is not exposed in production
- Secrets are injected at runtime only

---

## Production Endpoints

| Service        | URL                                          |
|----------------|----------------------------------------------|
| Frontend       | https://ofspain.click                        |
| API            | https://api.ofspain.click                    |
| Health check   | https://api.ofspain.click/actuator/health    |
