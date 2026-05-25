# 🚀 GitHub Actions → AWS Secrets Manager CI/CD Pipeline (Agent Spec)

---

## 📌 CONTEXT

You are working on a production system called **RideList**, which runs across:

* **EC2 (current staging environment using Docker Compose)**
* **Future EKS (Kubernetes production environment)**

The system uses **AWS Secrets Manager** as the central source of truth for all sensitive configuration.

The application expects environment variables like:

* DB credentials (`DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`)
* JWT config (`JWT_SECRET`, `JWT_EXPIRATION`, `JWT_REFRESH_EXPIRATION`)
* SMTP config (`SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`)
* AWS config (`AWS_REGION`, `AWS_S3_BUCKET`)
* App config (`FRONTEND_BASE_URL`, etc.)

---

## 🎯 GOAL

Design and implement a **GitHub Actions pipeline** that securely:

1. Pushes environment-specific secrets to AWS Secrets Manager
2. Prevents accidental overwrite or deletion of unrelated keys
3. Supports multiple environments:

   * `test`
   * `prod`
4. Enables safe updates (merge strategy, not destructive replacement)
5. Supports rollback of secrets to a previous version
6. Works with JSON-based Secrets Manager secrets (NOT individual key/value secrets per variable)
7. Integrates with AWS IAM securely (no long-lived AWS keys in code if possible)
8. Produces audit-friendly deployments

---

## 🧱 CURRENT ARCHITECTURE CONTEXT

### EC2 staging flow (already implemented):

```text
GitHub Actions (future)
        ↓
AWS Secrets Manager
        ↓
EC2 User Data (config-loader.sh)
        ↓
/opt/ridelist/.env
        ↓
Docker Compose
        ↓
Spring Boot App
```

---

## 🧱 SECRET STRUCTURE IN AWS

Each environment uses grouped secrets:

```text
/ridelist/{env}/database
/ridelist/{env}/jwt
/ridelist/{env}/smtp
/ridelist/{env}/aws
/ridelist/{env}/app-config
```

Each secret is a JSON object like:

```json
{
  "DB_USERNAME": "value",
  "DB_PASSWORD": "value"
}
```

---

## 🔐 SECURITY REQUIREMENTS

The pipeline MUST:

### Authentication

* Use GitHub OIDC → AWS IAM Role assumption (preferred)
* Avoid storing `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in GitHub secrets if possible

### Safety

* If fallback is needed, isolate and secure credentials
* Encrypt all secrets in transit (AWS SDK default acceptable)
* Never echo secrets in logs
* Mask sensitive values in GitHub Actions logs

---

## 🧠 REQUIRED BEHAVIOR (VERY IMPORTANT)

### 1. Safe update strategy (NO DATA LOSS)

When updating a secret:

* Fetch existing secret JSON
* Merge with new values
* Only overwrite changed keys
* Preserve unknown keys (forward compatibility)

---

### 2. Rollback strategy

Implement versioning strategy using:

* AWS Secrets Manager native versioning (`AWSPREVIOUS` stage OR version IDs)
* OR backup before overwrite:

```text
s3://ridelist-secret-backups/{env}/{secret-name}/{timestamp}.json
```

---

### 3. Environment separation

Pipeline must support:

* `test`
* `prod`

Selection via:

```yaml
env:
  ENVIRONMENT: staging
```

Secrets path mapping:

```text
/ridelist/staging/*
/ridelist/prod/*
```

---

## ⚙️ REQUIRED OUTPUT

### 1. GitHub Actions workflow

File:

```text
.github/workflows/secrets-sync.yml
```

Must include:

* workflow_dispatch OR push trigger
* environment input parameter
* AWS auth (prefer OIDC role assumption)
* JSON merge logic
* Secrets Manager update calls

---

### 2. Reusable script OR inline step

Preferred language:

* Node.js OR Python (NOT bash-heavy)

Must handle:

* reading JSON secrets
* merging updates
* pushing to AWS Secrets Manager

---

### 3. IAM role policy (minimum required permissions)

Must include:

* `secretsmanager:GetSecretValue`
* `secretsmanager:PutSecretValue`
* `secretsmanager:DescribeSecret`
* `secretsmanager:ListSecretVersionIds`
* `s3:PutObject` (if backup enabled)
* `kms:Encrypt` (if custom KMS used)

---

### 4. Safety checks

Pipeline must include:

* confirmation step for production changes
* diff preview of secret changes before apply
* prevention of empty overwrite (`{}`) (critical safeguard)

---

## 🚨 FAILURE MODES TO PREVENT

The system must explicitly avoid:

* overwriting secrets with empty JSON `{}` accidentally
* deleting keys when partial update is pushed
* leaking secrets in logs
* mixing environments accidentally
* untracked manual console changes being silently overwritten

---

## 🧪 OPTIONAL (BUT PREFERRED)

If possible, include:

* GitHub Actions dry run mode
* secret diff output in PR comments
* rollback workflow (restore previous secret version)

---

## 📌 FINAL EXPECTATION

Produce a production-grade, safe, maintainable GitHub Actions → AWS Secrets Manager pipeline that can later scale into EKS without changes to application logic.
