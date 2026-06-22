# RideList Ansible Infrastructure

This document defines the structure, responsibilities, and evolution roadmap for the RideList Ansible automation layer. Ansible manages the configuration and lifecycle of all infrastructure resources provisioned by the AWS CDK (Python) codebase.

---

## 1. Repository Tree

`
ansible/
│
├── README.md
├── collections/
│   └── requirements.yml
│
├── group_vars/
│   ├── test.yml
│   └── prod.yml
│
├── host_vars/
│   └── .gitkeep
│
├── inventories/
│   ├── test/
│   │   └── hosts.yml
│   └── prod/
│       └── hosts.yml
│
├── playbooks/
│   ├── bootstrap.yml
│   ├── deploy.yml
│   └── validate.yml
│
└── roles/
    ├── application/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── certbot/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── common/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── docker/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── eks-bootstrap/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── ingress/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── k3s/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── kubernetes/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── monitoring/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── nginx/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── observability/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    ├── secrets/
    │   ├── defaults/main.yml
    │   ├── files/
    │   ├── handlers/main.yml
    │   ├── meta/main.yml
    │   ├── tasks/main.yml
    │   ├── templates/
    │   └── vars/main.yml
    │
    └── storage/
        ├── defaults/main.yml
        ├── files/
        ├── handlers/main.yml
        ├── meta/main.yml
        ├── tasks/main.yml
        ├── templates/
        └── vars/main.yml
`

---

## 2. Directory Responsibilities

### ansible/

* **Why it exists:** Serves as the root directory for all Ansible automation. Isolates configuration management logic from the CDK infrastructure definitions residing at the repository root.
* **What belongs there:** Playbooks, inventories, roles, variables, collections requirements, and architectural documentation.
* **What should never be placed there:** CDK source code, application source code, built artifacts, secrets in plaintext, environment-specific state files, or compiled Python bytecode.
* **How it interacts:** This directory is the execution context for ansible-playbook. It consumes dynamic inventory data (for example, EC2 instance details published by CDK into SSM Parameters) and pushes configuration changes to the provisioned compute layer.

---

### ansible/collections/

* **Why it exists:** Holds the requirements.yml file used to declare external Ansible Collections (for example, amazon.aws, community.aws, or community.docker) that the automation depends upon.
* **What belongs there:** Only collection requirement manifests and collection metadata.
* **What should never be placed there:** Actual collection code (which is installed via ansible-galaxy into the local environment, not committed), nor custom roles.
* **How it interacts:** Provides portable dependency management so that CI/CD runners and operator workstations can install the exact same set of collection versions before executing playbooks.

---

### ansible/group_vars/

* **Why it exists:** Stores environment-scoped variable files that apply to logical groups of hosts (test, prod, and future expansions).
* **What belongs there:** High-level variables such as environment identifiers, feature flags, AWS region references, logging levels, and non-secret defaults that differ between test and production.
* **What should never be placed there:** Host-specific overrides, secrets, or hard-coded resource IDs. Those belong in host_vars/, AWS Secrets Manager, or SSM Parameter Store.
* **How it interacts:** Playbooks target inventory groups; Ansible automatically merges group_vars into the variable precedence hierarchy. This enforces environment isolation without duplicating playbook logic.

---

### ansible/host_vars/

* **Why it exists:** Reserved for host-specific variable overrides when an individual instance diverges from its group defaults (for example, a dedicated utility node).
* **What belongs there:** Files named after individual inventory hostnames containing isolated overrides.
* **What should never be placed there:** Broad environment variables, secrets at rest, or dynamic resource IDs that change with every CDK deployment.
* **How it interacts:** Ansible loads these with the highest static-file precedence. Use sparingly; prefer dynamic lookups via amazon.aws.aws_ssm for host-specific IDs generated by CDK.

---

### ansible/inventories/

* **Why it exists:** Defines the target hosts for each environment. In a cloud-native context, the inventory is often dynamic or references CDK-generated resource tags.
* **What belongs there:** Per-environment inventory files (hosts.yml) that define groups, children, and potentially dynamic inventory plugin configurations.
* **What should never be placed there:** Playbooks, roles, or variable definitions. Variable logic stays in group_vars/ and host_vars/.
* **How it interacts:** Playbooks invoke an inventory via -i inventories/test/ or -i inventories/prod/. Inventories may reference EC2 tags or SSM Parameters populated by CDK to discover instance public IPs or Elastic IPs.

---

### ansible/inventories/test/ and ansible/inventories/prod/

* **Why it exists:** Provides strict environment separation at the inventory level, preventing accidental cross-environment execution.
* **What belongs there:** The hosts.yml inventory manifest for that single environment, plus any dynamic inventory scripts or plugin configurations specific to that environment.
* **What should never be placed there:** Variables should not be embedded directly; link to the global group_vars directory or use group_vars directories inside the inventory folder only if environment encapsulation is required.
* **How it interacts:** CI/CD pipelines select the appropriate directory at invocation time (-i inventories/test/). CDK provisions entirely separate VPCs and instances per environment; the inventory layer maps Ansible to those isolated resources.

---

### ansible/playbooks/

* **Why it exists:** Contains the top-level orchestration files that express the desired end-state of the infrastructure in a specific sequence.
* **What belongs there:** High-level playbooks (bootstrap.yml, deploy.yml, validate.yml) that import roles and define execution order.
* **What should never be placed there:** Low-level task definitions, Jinja2 templates, or role-specific defaults. Playbooks should be thin orchestration layers.
* **How it interacts:** Playbooks consume inventories and apply roles to hosts. They act as the public API of the configuration layer; operators and automation should only ever invoke playbooks, never individual roles.

---

### ansible/roles/

* **Why it exists:** Encapsulates reusable, self-contained units of configuration. Each role addresses a single concern (for example, installing Docker or mounting storage).
* **What belongs there:** Role directories, each representing a bounded domain of system configuration.
* **What should never be placed there:** One-off scripts, ad-hoc playbooks, or documentation unrelated to a specific role.
* **How it interacts:** Roles are imported by playbooks. They are independent of inventories and should function correctly regardless of environment when supplied with appropriate variables.

---

### roles/<role_name>/defaults/main.yml

* **Why it exists:** Defines the lowest precedence variables for the role, establishing safe, overrideable defaults.
* **What belongs there:** Role-specific variables such as package names, file paths, default feature flags, or timeout values.
* **What should never be placed there:** Secrets, environment-specific identifiers, or assumptions about the host group.
* **How it interacts:** Variables defined here are automatically loaded when the role is used. They are overridden by group_vars, host_vars, extra vars, and vars/main.yml.

---

### roles/<role_name>/vars/main.yml

* **Why it exists:** Holds role-internal variables that should not be easily overridden by the end user but are not secret.
* **What belongs there:** Internal constants, derived facts, or lookup results that the role must rely upon as immutable within its own execution.
* **What should never be placed there:** Secrets or variables that differ per environment.
* **How it interacts:** Loaded after defaults/ and before group_vars, offering a middle tier of precedence for role authors.

---

### roles/<role_name>/tasks/main.yml

* **Why it exists:** The primary execution entrypoint for the role. Ansible starts here when the role is included.
* **What belongs there:** A curated list of include_tasks or import_tasks calls that loads discrete task files, or a flat list of task invocations.
* **What should never be placed there:** Complex Jinja2 logic, variable definitions, or handlers. Keep it declarative and readable.
* **How it interacts:** Executed in order when the role is applied. Should delegate to sub-task files for readability as roles grow.

---

### roles/<role_name>/handlers/main.yml

* **Why it exists:** Defines state-change reactions, such as restarting a service after a configuration file is modified.
* **What belongs there:** Handler definitions triggered by tasks within the role or other roles.
* **What should never be placed there:** Long-running deployment tasks or health checks. Handlers should be lightweight and idempotent.
* **How it interacts:** Listened to via notify directives in tasks. Handlers run once at the end of a play block, even if notified multiple times.

---

### roles/<role_name>/templates/

* **Why it exists:** Stores Jinja2 templates that generate dynamic configuration files on the target host.
* **What belongs there:** Template files with the .j2 extension for service configurations, environment files, systemd units, or virtual host definitions.
* **What should never be placed there:** Static files that do not require variable substitution (those belong in files/), or binary blobs.
* **How it interacts:** Referenced by the template module in tasks. Variables from defaults/, vars/, and group variables are rendered at runtime.

---

### roles/<role_name>/files/

* **Why it exists:** Stores static, verbatim files to be copied to the target host without transformation.
* **What belongs there:** Static scripts, binary artifacts, public keys, or baseline configuration files that are identical across environments.
* **What should never be placed there:** Files requiring environment-specific values, credentials, or Jinja2 logic. Use templates/ instead.
* **How it interacts:** Referenced by the copy module in tasks. Files are deployed exactly as they exist in the repository.

---

### roles/<role_name>/meta/main.yml

* **Why it exists:** Declares role metadata, including dependencies on other roles, supported platforms, and author information.
* **What belongs there:** Dependency lists (for example, nginx depending on common), minimum Ansible version requirements, and galaxy metadata.
* **What should never be placed there:** Variable definitions, task logic, or inventory references.
* **How it interacts:** Ansible processes this file before executing the role. If dependencies are listed, Ansible ensures they run first, enabling proper composition and ordering.

---

## 3. Playbook Responsibilities

### bootstrap.yml

**Purpose:**
Initial machine preparation after CDK deployment.

**Responsibilities:**

* **OS preparation:** Ensure the base operating system is updated with required repositories, kernel parameters, and timezone settings.
* **Docker installation:** Install the Docker Engine, the Docker CLI, and the Docker Compose plugin. Configure the Docker daemon options suitable for the instance profile.
* **Storage initialization:** Discover and prepare the EBS volume provisioned by CDK. Create filesystems, define mount points in /etc/fstab, and mount the volume persistently.
* **Secrets bootstrap:** Establish the IAM role trust and AWS CLI / SDK access paths so that subsequent roles can retrieve values from AWS Secrets Manager and SSM Parameter Store.
* **Nginx preparation:** Install the Nginx package and prepare the directory structure for virtual host definitions and SSL certificates. Do not yet enable full application proxying.

**Typical Roles Applied:** common -> storage -> docker -> secrets -> nginx

---

### deploy.yml

**Purpose:**
Application deployment and update workflow.

**Responsibilities:**

* **Pull images:** Authenticate with Amazon ECR (using the EC2 instance IAM role) and pull the correct application container image tags for the target environment.
* **Deploy containers:** Update the Docker Compose project (or future Kubernetes manifests) with the latest image references, environment variables, and network bindings.
* **Update configuration:** Render application-level configuration files, reverse proxy definitions, and environment files from templates using live values from Secrets Manager and SSM.
* **Restart services:** Trigger controlled restarts of Nginx and application containers so changes take effect with minimal downtime.

**Typical Roles Applied:** secrets -> application -> nginx -> certbot

---

### validate.yml

**Purpose:**
Infrastructure and application health verification.

**Responsibilities:**

* **Verify mounts:** Confirm that the EBS volume is mounted at the expected path and is writable.
* **Verify secrets:** Assert that the environment file exists on disk, contains the expected keys, and that the application can read configuration without error.
* **Verify application availability:** Perform an HTTP health check against the application endpoint (via localhost or Elastic IP) and assert a successful response code.
* **Verify SSL:** Validate that TLS certificates are present, not expired, and correctly served by Nginx for the configured domain.
* **Verify network connectivity:** Confirm that the EC2 instance can reach AWS services (ECR, Secrets Manager, S3) and that the Security Group rules allow intended ingress/egress traffic.

**Typical Roles Applied:** storage (verification) -> secrets (verification) -> application (health checks) -> nginx -> certbot

---

## 4. Role Responsibilities

### common

Responsible for:

* Base OS packages: Installation of essential utilities (for example, jq, curl, awscli, htop, unzip, ntp or chrony).
* Utility installation: Bootstrapping tools required by later roles, such as Python pip or the AWS Systems Manager agent.
* System configuration: Hostname alignment, kernel tuning for networking and filesystems, log rotation policies, and standard user/group creation.

**Interaction with CDK:** Assumes IAM role and SSM connectivity are already established by CDK. Uses standard Amazon Linux / Ubuntu AMI packages; does not hardcode resource IDs.

---

### storage

Responsible for:

* EBS preparation: Discovery of the attached EBS volume via device naming conventions or AWS API lookups.
* Filesystems: Idempotent creation of filesystems (ext4 or xfs) only if a filesystem header is absent.
* Mount points: Creation of persistent mount directories and updates to /etc/fstab.
* Persistent directories: Provisioning subdirectories on the mounted volume for application data, container volumes, and logs.

**Interaction with CDK:** The volume ID and device mapping are published to SSM Parameters by CDK; this role either reads them dynamically or accepts them as parameterized variables.

---

### docker

Responsible for:

* Docker installation: Adding the official Docker repository and installing the Engine.
* Docker Compose installation: Installing the Docker Compose plugin or standalone binary depending on the target OS lifecycle.
* Runtime configuration: Setting daemon options such as log drivers, surge limits, and insecure registries if required for ECR asset retrieval in VPC-limited environments.

**Interaction with CDK:** Relies on the IAM Role (attached to the EC2 instance by CDK) for ECR authentication. No direct resource dependencies beyond standard OS repositories.

---

### secrets

Responsible for:

* AWS Secrets Manager retrieval: Fetching application secrets and database credentials using the EC2 instance profile.
* Environment file generation: Templating a secure .env or application-specific environment file on the host filesystem with restrictive permissions.
* Secret validation: Verifying that all expected secret keys are present and non-empty before application containers start.

**Interaction with CDK:** CDK creates the Secrets Manager secrets and the IAM policy permitting secretsmanager:GetSecretValue. This role consumes those outputs at runtime.

---

### nginx

Responsible for:

* Reverse proxy configuration: Templating the primary Nginx configuration and per-application virtual host files that forward traffic to container ports.
* Virtual hosts: Enabling or disabling server blocks based on the application topology and environment.
* TLS integration: Referencing certificate and key paths provisioned by the certbot role, and configuring modern SSL parameters.

**Interaction with CDK:** Expects the Security Group (created by CDK) to allow ingress on TCP 80 and TCP 443. Elastic IP association performed by CDK gives Nginx a stable public endpoint.

---

### certbot

Responsible for:

* Certificate issuance: Obtaining TLS certificates from Let us Encrypt via HTTP-01 or DNS-01 challenges, gated by the presence of a valid domain and public reachability.
* Renewal: Installing a systemd timer or cronjob for automated certificate renewal before expiry.
* Validation: Verifying that the certificate chain is complete and that Nginx serves it correctly.

**Interaction with CDK:** Requires the Security Group to expose port 80 for challenge validation, and the Route 53 hosted zone (or external DNS) to resolve the domain to the Elastic IP provisioned by CDK.

---

### application

Responsible for:

* Application deployment: Managing the Docker Compose project lifecycle: up, down, pull, and recreate.
* Container lifecycle: Enforcing restart policies, resource limits, and network attachment for application services.
* Service health checks: Post-deployment smoke tests and readiness checks before marking the deployment as successful.

**Interaction with CDK:** Pulls images from ECR repositories provisioned by CDK. Consumes the EBS mount (prepared by storage) for persistent state and the environment file (generated by secrets) for configuration. The Security Group and Elastic IP determine external accessibility.

---

## 5. Future Evolution

### Phase 1: Docker Compose on EC2

Current State.
The repository layout above directly supports running containerized workloads on a single EC2 instance using Docker Compose. Roles are sharply scoped:

- docker installs the runtime.
- application manages docker compose up/down.
- nginx terminates TLS and proxies to the Compose service ports.
- certbot manages certificates on the host.

---

### Phase 2: k3s on EC2

Transition Path.
When Docker Compose is replaced by a lightweight Kubernetes distribution (k3s) on the same EC2 instance(s), the structure evolves as follows:

**Unchanged Roles:**
- common - still prepares the OS.
- storage - still mounts EBS volumes; Kubernetes will consume them as hostPath or via local persistent volumes.
- secrets - still fetches values from AWS Secrets Manager. It will now generate Secret manifest files or inject values into Helm values instead of .env files.
- nginx - Can optionally remain as a host-level reverse proxy in front of k3s NodePorts, though it is more likely to be superseded by in-cluster ingress.
- certbot - May transition to in-cluster cert-manager, but can remain if host-level certificates are still needed.

**Replaced Roles:**
- docker - Replaced by k3s for installing the k3s server/agent binaries and configuring the kubeconfig.
- application - Replaced by kubernetes and ingress for applying Deployments, Services, and Ingress resources instead of Docker Compose files.

**New Roles:**
- k3s - Installs k3s, sets up the kubeconfig, and optionally joins agent nodes.
- kubernetes - Applies Kubernetes manifests or Helm charts for application workloads.
- ingress - Installs and configures an Ingress Controller (for example, Traefik, which ships with k3s, or NGINX Ingress) and defines Ingress rules for routing and TLS termination.
- monitoring - Deploys node-level and cluster-level metric collection (Prometheus node-exporter, kube-state-metrics).
- observability - Deploys log aggregation and tracing agents.

---

### Phase 3: Amazon EKS

Transition Path.
When moving to Amazon EKS, the control plane is fully managed by AWS. Ansible shifts from cluster installation to node preparation and cluster bootstrapping.

**Unchanged Roles:**
- common - OS baseline remains required for EKS managed and self-managed nodes.
- storage - EBS CSI driver node requirements and volume attachments still need host-level preparation on certain node configurations.
- secrets - Still retrieves secrets; these may be synchronized into EKS via AWS Secrets and Configuration Provider (ASCP) or External Secrets Operator.
- monitoring - Remains relevant for node-level daemonsets and custom observability agents.
- observability - Remains relevant for log shippers and tracing sidecars.

**Replaced Roles:**
- k3s - Replaced by eks-bootstrap because k3s is no longer used.
- docker - Replaced by containerd configuration managed by the EKS AMI or by eks-bootstrap for custom AMI tuning.
- nginx (host-level) - Fully replaced by ingress running inside the EKS cluster.
- certbot (host-level) - Fully replaced by cert-manager inside the cluster, managed via the kubernetes role.
- application (Compose logic) - Fully replaced by kubernetes applying manifests to the EKS API server.

**New Roles:**
- eks-bootstrap - Prepares EC2 instances to join an EKS cluster: installs aws-cli, eksctl (if needed), the IAM Authenticator, kubeconfig generation, and node label/taint alignment.
- ingress - Evolves to install AWS Load Balancer Controller or NGINX Ingress Controller as an EKS addon or Helm release, and manages IngressClass resources.
- kubernetes - Evolves to apply higher-order abstractions (Deployments, Services, Ingresses, HPA, PDBs) via kubernetes.core collection modules or Helm.

**Structural Impact:**
- Playbooks change from targeting individual EC2 instances to a two-stage model:
  1. bootstrap.yml targets EKS node groups for AMI and daemon preparation.
  2. deploy.yml targets the EKS control plane (via kubectl/Helm from a CI runner or bastion) to apply Kubernetes manifests.
- inventories/ may split into node inventory (for EC2 bootstrapping) and cluster inventory (for Kubernetes context targeting).

---

## 6. Design Principles

### Separation of Concerns

Each role owns exactly one bounded domain. Playbooks own orchestration. Variables own configuration. Hosts and groups own targeting. No role embeds playbook logic, and no playbook implements low-level package installation.

### Idempotency

Every role and playbook is designed to be run multiple times without side effects. Package installations use modules that check state first. File changes use handlers that trigger restarts only when content changes. Storage operations inspect existing filesystem headers before formatting.

### Environment Isolation

Inventories, group_vars, and CI/CD invocations are strictly separated by environment (test vs prod). There is no single inventory that accidentally spans both. Variables do not silently fall back to production values when test values are absent.

### Reusability

Roles avoid hardcoding resource IDs, domain names, or secrets. They accept variables via defaults/ and vars/. The same role can run in test, prod, or a local Vagrant box without source modification.

### Future EKS Migration Support

The role taxonomy is intentionally aligned with Kubernetes concepts. application today deploys containers; tomorrow, kubernetes deploys pods. nginx today configures virtual hosts; tomorrow, ingress configures Ingress resources. This mapping minimizes retraining and refactoring effort during Phase 3.

### Minimal Duplication

Shared logic (for example, installing AWS CLI, creating standard directories, or restarting services) belongs in common or dedicated utility roles. Roles declare dependencies via meta/main.yml rather than duplicating tasks. Templates and files are stored in the role that consumes them.

---

## 7. How Roles Interact with CDK-Provisioned Infrastructure

The CDK stack owns the what and where of infrastructure. Ansible owns the how of runtime configuration. Their contract is realized through the following interfaces:

1. **IAM Roles:** CDK creates the IAM Role and Instance Profile attached to the EC2 instance. Ansible does not create IAM policies; it assumes their existence to make AWS API calls (Secrets Manager, ECR, S3, SSM).
2. **SSM Parameters:** CDK writes dynamic identifiers (instance IDs, volume IDs, Elastic IPs, ECR repository URIs) into SSM Parameter Store. Ansible roles perform lookups against these parameters so that playbooks remain generic and do not hardcode Terraform/CDK outputs.
3. **Security Groups:** CDK defines ingress/egress rules. Ansible roles (for example, nginx and certbot) rely on those rules being present; they do not modify AWS security groups. If a role needs a port open, the requirement is documented and fed back to the CDK definition, not applied via ad-hoc AWS CLI calls in Ansible.
4. **Elastic IP:** CDK allocates and associates the Elastic IP. Ansible roles (nginx, certbot) assume a stable public endpoint exists for DNS and TLS validation.
5. **EBS Volume:** CDK creates and attaches the volume. The storage role discovers it (via SSM or predictable device mapping) and handles filesystem and mount concerns.
6. **ECR Repositories:** CDK provisions repositories and lifecycle policies. The application role authenticates and pulls using the IAM role; repository URIs are injected via SSM or group variables.
7. **Secrets Manager:** CDK defines secrets and rotation policies. The secrets role reads them at runtime and writes them to the local filesystem in the format the application expects.
8. **S3 Buckets:** CDK creates buckets for assets or backups. Ansible tasks may read from or write to these buckets using the instance IAM role, but they do not create or destroy them.

This strict handoff ensures that the infrastructure lifecycle (create/destroy) remains in CDK, while the configuration lifecycle (bootstrap/deploy/validate) remains in Ansible.


# Execution

bootstrap.yml
│
├── Load all.yml
│
├── Load {env}.yml
│
├── pre_tasks
│   ├── debug
│   └── validate aws region
│
├── role: storage
│
├── role: secrets
│
├── role: docker
│
├── role: application
│
├── role: certbot
│   │
│   ├── defaults/main.yml
│   │
│   ├── vars/main.yml
│   │
│   ├── tasks/main.yml
│   │   │
│   │   ├── install.yml
│   │   │   └── yum install certbot
│   │   │
│   │   └── issue.yml
│   │       ├── create webroot
│   │       ├── stop nginx
│   │       ├── issue cert
│   │       ├── chmod letsencrypt
│   │       └── start nginx
│   │
│   └── handlers (only if notified)
│
├── role: nginx
│
└── post_tasks
    └── deployment summary
