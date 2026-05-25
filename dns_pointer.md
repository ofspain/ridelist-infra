# EC2 + CDK + Cloudflare + Nginx Deployment Flow (Elastic IP + Certbot)

This document describes the full production flow for deploying an EC2-based Docker stack behind Cloudflare with an Elastic IP and SSL via Certbot.

---

# 1. High-Level Architecture

```
Cloudflare DNS
↓
Elastic IP (AWS)
↓
EC2 Instance
↓
Nginx (Docker container)
↓
Frontend + Backend services (Docker Compose)
```

---

# 2. Responsibilities Breakdown

## CDK (Infrastructure Layer)

* Provisions EC2 instance
* Allocates Elastic IP
* Attaches Elastic IP to EC2
* Installs base dependencies via user-data:

  * Docker
  * Docker Compose
  * Certbot
  * system packages
* Creates required directories

---

## Cloudflare (DNS Layer)

* Hosts DNS records for domain
* Maps domain → Elastic IP
* Optional: acts as proxy/CDN later

---

## EC2 Instance (Runtime Layer)

* Runs Docker Compose stack
* Hosts Nginx reverse proxy
* Runs Certbot for SSL issuance
* Stores persistent data on EBS volume

---

## Certbot (SSL Layer)

* Issues SSL certificates via Let’s Encrypt
* Validates domain ownership via HTTP challenge
* Stores certs in `/etc/letsencrypt`

---

# 3. Provisioning Sequence (Correct Order)

## Step 1 — CDK Deployment

CDK provisions:

* EC2 instance
* Elastic IP
* Association between EIP and instance
* Security groups (port 80, 443, 22)
* User-data bootstrap

### Expected Output

```
ElasticIP = 3.120.xxx.xxx
```

This is the stable endpoint for DNS.

---

## Step 2 — DNS Configuration (Cloudflare)

After CDK completes:

Create DNS records:

```
A ofspain.click → <Elastic IP>
A api.ofspain.click → <Elastic IP>
```

Recommended initially:

* Proxy: DNS only (grey cloud)

---

## Step 3 — Wait for DNS Propagation

Verify resolution:

```bash
dig ofspain.click +short
```

Expected:

```
<Elastic IP>
```

Also verify HTTP reachability:

```bash
curl http://ofspain.click
```

---

## Step 4 — SSL Certificate Issuance (Certbot)

Once DNS resolves correctly:

### Option A (Recommended): Standalone Mode

Temporarily uses port 80 directly.

```bash
sudo certbot certonly --standalone \
  -d ofspain.click \
  -d api.ofspain.click
```

### Requirements:

* Port 80 must be open
* No other service using port 80 during issuance

### Output:

```
/etc/letsencrypt/live/ofspain.click/
```

Contains:

* fullchain.pem
* privkey.pem

---

## Step 5 — Start Application Stack

Deploy Docker Compose:

```bash
docker compose up -d
```

This starts:

* Nginx reverse proxy
* Frontend container
* Backend container

---

## Step 6 — Switch to HTTPS Mode (Nginx)

Ensure nginx config references:

```
/etc/letsencrypt/live/ofspain.click/fullchain.pem
/etc/letsencrypt/live/ofspain.click/privkey.pem
```

Then restart nginx container:

```bash
docker compose restart nginx
```

---

# 4. Final Production State

```
HTTPS Users
    ↓
Cloudflare DNS
    ↓
Elastic IP (static AWS endpoint)
    ↓
Nginx (SSL termination)
    ↓
Frontend / Backend (Docker)
```

---

# 5. Key Design Principles

## 5.1 Stability via Elastic IP

* EC2 can restart or be replaced
* IP remains constant
* DNS never needs frequent updates

---

## 5.2 Separation of Concerns

* CDK → infrastructure
* Cloudflare → DNS routing
* Certbot → SSL lifecycle
* Docker → application runtime

---

## 5.3 Bootstrap Safety Rule

Certbot must run only when:

* Domain resolves to EC2
* Port 80 is reachable publicly
* Nginx is not blocking challenge (or using standalone mode)

---

# 6. Common Failure Points

## DNS not propagated

```
dig returns nothing or old IP
```

Fix: wait or recheck Cloudflare records

---

## Certbot fails validation

* DNS not pointing correctly
* Port 80 blocked
* Proxy enabled in Cloudflare

---

## Nginx fails on startup

* Missing cert files before issuance

Fix:

* use HTTP-only config first OR issue cert first

---

# 7. Recommended Improvements (Optional)

## 7.1 Use Cloudflare Proxy Later

* Enable orange cloud after SSL works
* Adds caching + DDoS protection

---

## 7.2 Replace Certbot with Cloudflare Origin Certs

* No renewal needed
* No HTTP challenges
* Simpler long-term ops

---

## 7.3 Fully automate Certbot renewal

* Already handled via system timers on most Linux installs

---

# 8. Summary Flow

```
CDK deploy
   ↓
Elastic IP created
   ↓
DNS pointed (Cloudflare)
   ↓
DNS resolves to EC2
   ↓
Certbot issues SSL
   ↓
Docker stack starts
   ↓
Nginx serves HTTPS traffic
```
