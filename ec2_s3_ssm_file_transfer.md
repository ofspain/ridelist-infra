# File Transfer to EC2 Using S3 + SSM (No SSH Required)

## Overview
This method allows you to transfer files to an EC2 instance without using SSH or a `.pem` key. It uses Amazon S3 as a staging area and AWS Systems Manager (SSM) to access the instance securely.

---

## Step 1 — Upload File from Local Machine to S3

Run this command on your **local computer**:

```bash
aws s3 cp localfile.txt s3://your-bucket-name/
```

### What this does:
- Uploads `localfile.txt` from your local machine
- Stores it in the specified S3 bucket
- Makes the file accessible to your EC2 instance

---

## Step 2 — Start an SSM Session to EC2

Run this from your **local machine**:

```bash
aws ssm start-session --target i-xxxx
```

### What this does:
- Opens a secure shell session to your EC2 instance
- Does NOT use SSH or key pairs
- Requires proper IAM role and SSM agent on the instance

---

## Step 3 — Download File from S3 to EC2

Inside the EC2 session, run:

```bash
aws s3 cp s3://your-bucket-name/localfile.txt /home/ec2-user/
```

### What this does:
- Pulls the file from S3
- Places it into the EC2 instance filesystem

---

## Requirements

For this workflow to function, your EC2 instance must have:

- AWS Systems Manager (SSM) Agent installed
- IAM role with `AmazonSSMManagedInstanceCore` policy attached
- Network access to SSM (via internet or VPC endpoints)
- Access to the S3 bucket used for file storage

---

## Advantages

- No SSH or `.pem` key required
- No port 22 exposure
- Works directly from AWS Console or CLI
- Secure IAM-based access control
- Highly scalable for automation

---

## Summary Flow

```
Local Machine
    ↓ (aws s3 cp)
S3 Bucket
    ↓ (aws ssm session)
EC2 Instance
    ↓ (aws s3 cp)
Local filesystem on EC2
```
