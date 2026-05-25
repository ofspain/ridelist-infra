# 🚀 AGENT PROMPT: Fully Automated CDK + EC2 Bootstrap (Cloudflare + Nginx + Docker + SSL)

---

## 🎯 ROLE

You are a **senior AWS CDK + DevOps engineer**.

You are building a **fully automated infrastructure system** for a production-grade application called **RideList**.

The system runs on:

* AWS EC2 (single-instance test/staging environment)
* Docker Compose (application runtime)
* Nginx (reverse proxy)
* Cloudflare (DNS + edge routing)
* Elastic IP (stable public endpoint)
* Certbot OR Cloudflare-origin SSL automation
* AWS Secrets Manager (for configuration injection)

---

## 🧠 CORE OBJECTIVE

Design and implement a **fully automated CDK deployment** where:

> Running `cdk deploy` results in a fully working HTTPS system with zero manual SSH steps.

---

## ⚙️ REQUIRED OUTPUT

You must generate:

---

### 1. CDK INFRASTRUCTURE (Python)

Include stacks or modules for:

* VPC (simple public subnet for test environment)
* EC2 instance (Amazon Linux 2023 preferred)
* Elastic IP
* Security Group:

  * Port 80 (HTTP)
  * Port 443 (HTTPS)
  * SSH optional (env-controlled)
* IAM Role:

  * SSM access
  * ECR pull access
  * S3 access
  * Secrets Manager read access

---

### 2. USER DATA BOOTSTRAP SCRIPT (FULLY AUTOMATED)

The EC2 user-data MUST:

#### System setup

* Update OS
* Install Docker
* Install Docker Compose
* Install Nginx (if needed outside container)
* Install AWS CLI
* Install Certbot OR Cloudflare Origin Certificate dependencies

---

#### Application bootstrap

* Pull Docker images from ECR:

  * frontend
  * backend
* Create required directories:

  * `/data`
  * `/data/uploads`
  * `/opt/ridelist`
* Configure environment from AWS Secrets Manager:

  * `/ridelist/{env}/database`
  * `/ridelist/{env}/jwt`
  * `/ridelist/{env}/smtp`
  * `/ridelist/{env}/app-config`
* Render `.env` file automatically

---

#### Docker Compose startup

Start full stack:

```
nginx
frontend
backend
postgres (optional for test env)
```

Ensure restart policy: `always`

---

#### SSL AUTOMATION (CRITICAL)

Implement ONE of the following:

### Option A (Preferred): Cloudflare Origin Certificates

* Generate or pre-create origin cert
* Inject via Secrets Manager or SSM
* Configure Nginx automatically
* No Certbot required
* No port 80 challenge dependency

### Option B: Certbot Fully Automated

* Use standalone or webroot mode
* Auto-detect domain from metadata or SSM
* Auto-issue certificate on first boot
* Auto-renew via cron/systemd

---

### 3. NGINX AUTO-CONFIGURATION

Generate Nginx config automatically via user-data:

* Reverse proxy:

  * `/` → frontend:3000
  * `/api` → backend:8080
* HTTPS enabled automatically
* Redirect HTTP → HTTPS
* Supports domains:

  * `ofspain.click`
  * `api.ofspain.click`

---

### 4. DOMAIN + CLOUDFLARE ASSUMPTION

Assume:

* DNS already points to Elastic IP
* Cloudflare proxy initially OFF (DNS only)

Do NOT automate Cloudflare API unless explicitly requested.

---

### 5. SAFE DEPLOYMENT GUARANTEES

System MUST ensure:

* Idempotent bootstrapping (safe reboots)
* No duplicate certificate issuance loops
* No overwriting valid configs
* No secrets in logs
* All secrets fetched securely (SSM / Secrets Manager only)

---

### 6. OBSERVABILITY (MINIMUM)

Include:

* Docker logs stored in `/var/log`
* Optional CloudWatch agent setup
* Health check endpoint `/health`

---

## 🚨 FAILURE CONDITIONS TO AVOID

Do NOT produce solutions that:

* Require manual SSH after deployment
* Require manual Certbot execution
* Store secrets in plaintext user-data
* Break on EC2 reboot
* Require post-deploy manual Nginx config
* Use hardcoded environment variables

---

## 🧭 ARCHITECTURE TARGET STATE

After `cdk deploy`:

```
Cloudflare DNS
    ↓
Elastic IP (AWS)
    ↓
EC2 (fully bootstrapped)
    ↓
Docker Compose running
    ↓
Nginx auto-configured
    ↓
HTTPS enabled
    ↓
Frontend + Backend live
```

---

## 📌 FINAL EXPECTATION

Produce:

* Clean CDK Python code
* Robust EC2 user-data bootstrap script
* Secure secrets injection flow
* Fully automated HTTPS setup
* Production-grade DevOps architecture

No manual steps.
No partial automation.

End state must be **zero-touch deployment after `cdk de
