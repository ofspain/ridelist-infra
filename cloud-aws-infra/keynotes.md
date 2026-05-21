```md
# 🚀 AWS CDK IAM Setup Journey (Bootstrap Success Guide)

## 📌 Goal
Prepare an AWS IAM user with the correct permissions to successfully run:

- `cdk bootstrap`
- `cdk deploy`
- AWS CDK-based infrastructure provisioning

---

# 1. Initial Problem State

We started with a CDK bootstrap failure due to permission issues.

## ❌ Root cause
The IAM user was affected by:

- `AWSCompromisedKeyQuarantineV3` policy (explicit DENY)
- IAM permission conflicts
- CDK bootstrap failing during role and bucket creation

## ❌ Impact
CDK could not create:

- IAM roles
- S3 asset bucket
- ECR repository
- CloudFormation execution roles

Even with admin-like permissions, the explicit deny blocked everything.

---

# 2. IAM Investigation Phase

We checked multiple IAM layers:

## 🔍 User-level policies
- No attached managed policies initially
- No inline policies found

## 🔍 Group-based inheritance
- User inherited `AdministratorAccess` via IAM group
- This explained missing direct attachments

## 🔍 Key discovery
Permissions were correct **except for one critical blocker:**

> ❗ AWSCompromisedKeyQuarantineV3 (explicit deny overrides everything)

---

# 3. Root Cause Fix

## 🔧 Action taken

- Removed `AWSCompromisedKeyQuarantineV3` policy
- Rotated AWS access credentials
- Verified correct IAM identity (`cdk-action-user`)
- Ensured no permission boundary restrictions

---

# 4. Final IAM State (Clean Setup)

## 👤 IAM User
- `cdk-action-user`

## 📦 Permissions model

### Group-based permissions
- `AdministratorAccess` ✔ (via IAM group)

### User-level policies
- None required ✔

### Inline policies
- None ✔

### Permission boundary
- None ✔

### Quarantine policy
- Removed ✔

---

# 5. CDK Bootstrap Execution

Once IAM was clean, CDK bootstrap succeeded.

## 🏗 Resources created (`CDKToolkit`)

- S3 asset bucket (`StagingBucket`)
- ECR repository (`ContainerAssetsRepository`)
- IAM roles:
  - `FilePublishingRole`
  - `ImagePublishingRole`
  - `CloudFormationExecutionRole`
  - `LookupRole`
  - `DeploymentActionRole`
- SSM parameter (`CdkBootstrapVersion`)
- Bucket policies

---

# 6. Final Result

```

✅ Environment aws://774173912604/eu-west-1 bootstrapped

````

### 🎉 Outcome
AWS environment is now fully ready for CDK deployments.

You can now run:

```bash
cdk deploy --profile ridelist-cdk
````

without additional IAM setup.

---

# 7. Key Learnings

## 🔑 IAM hierarchy matters

AWS evaluates permissions in this order:

1. Explicit DENY ❌ (most important)
2. User policies
3. Group policies ✔
4. Role policies
5. SCP / boundaries

---

## ⚠️ Important takeaway

Even with:

```json
"Action": "*",
"Resource": "*"
```

CDK will still fail if:

> An explicit deny exists anywhere in the identity chain

---

## 🧠 CDK bootstrap insight

CDK bootstrap is NOT “just setup” — it:

* creates IAM roles
* creates S3/ECR infrastructure
* configures deployment trust chain

So it requires **true admin-level permissions without deny constraints**.

---

# 🎯 Final State

You now have:

✔ Clean IAM user
✔ Admin-level permissions via group
✔ No quarantine or deny policies
✔ Successful CDK bootstrap
✔ Fully functional AWS CDK environment

---
### Improvement
If you want next step, I can show you how to move this into a **secure production setup (OIDC-based CDK deploys with zero long-lived keys)**.

```
```
