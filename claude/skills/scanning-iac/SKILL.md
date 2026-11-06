---
name: scanning-iac
description: >-
  Scan IaC (Terraform / Docker / K8s / Helm / GH Actions) for misconfigs,
  exposed secrets, public buckets, weak IAM, open SGs. Use before merging
  IaC changes.
allowed-tools: Bash(trivy *) Bash(checkov *) Bash(kube-score *) Bash(kubesec *) Bash(dockle *) Bash(actionlint *) Bash(tfsec *) Read Grep Glob
metadata:
  tags:
    - security
    - iac
    - terraform
    - docker
    - kubernetes
    - cicd
---

# Scanning IaC

IaC misconfigurations are responsible for a disproportionate share of cloud breaches. Scan before merge, every time.

## Tools

| Tool | Covers | Notes |
|---|---|---|
| **Trivy** | Terraform, Docker, K8s, Helm, CloudFormation, AWS CDK | One tool, broad coverage. Default for the kit |
| **Checkov** | Same as Trivy + Bicep + Serverless | Stronger policy-as-code, many built-in checks |
| **tfsec** | Terraform-only | Lightweight; subsumed by Trivy now |
| **kube-score** | K8s manifests | Best practices beyond security (also resource limits, probes) |
| **kubesec** | K8s manifests | Security-only |
| **dockle** | Container images | CIS Docker Benchmark |
| **actionlint** | GitHub Actions | Workflow syntax + security |

The kit's default: **Trivy + Checkov** (one or both — Trivy for breadth, Checkov for policy depth).

## Standard run

```bash
# All-in-one Trivy
trivy config infra/                    # Terraform, K8s, Docker
trivy config docker-compose.yml
trivy config .github/workflows/        # CI/CD too

# Or Checkov
checkov -d infra/ --quiet
checkov -d . --framework dockerfile,kubernetes,terraform,github_actions

# Kubernetes manifests (additional)
kube-score score k8s/*.yaml

# Container image (post-build)
trivy image --severity HIGH,CRITICAL <registry>/<image>:<tag>
```

`just security-scan` should run Trivy across all IaC dirs.

## Critical findings to never let through

- **Public S3 / GCS buckets** without `block_public_access` / `uniform_bucket_level_access`
- **`0.0.0.0/0` ingress** on non-loadbalancer security groups
- **Cleartext secrets** in env vars / TF vars / K8s configmaps
- **Privileged Docker containers** (`privileged: true`, `capabilities.add: SYS_ADMIN`)
- **`hostNetwork: true` / `hostPID: true`** in K8s pods (unless explicitly justified)
- **Wildcard IAM** (`Action: "*"`, `Resource: "*"`) outside admin roles
- **Missing encryption at rest** on RDS / S3 / EBS / disks
- **Missing TLS** (HTTP listeners, unencrypted traffic between services)
- **Latest tags** on container images (per `CLAUDE.md` § Safety floor, reference images by digest)
- **Long-lived access keys** instead of WIF / OIDC federation

## Per-domain checklists

### Terraform

- [ ] State backend is remote with encryption (S3+KMS, GCS+CMEK, Azure Storage with locks)
- [ ] State has lock (DynamoDB / GCS lock / Azure lease)
- [ ] No `0.0.0.0/0` security groups (or scoped via WAF / load balancer)
- [ ] `versioning = enabled` on state buckets
- [ ] `prevent_destroy = true` on critical resources (DBs, KMS keys)
- [ ] No secrets in `*.tfvars` (use SSM / Secret Manager / sealed secrets)
- [ ] One module per resource type
- [ ] Variables typed and validated

### Docker

- [ ] `FROM` uses immutable digest, not floating tag (`@sha256:...`)
- [ ] Multi-stage build with minimal final stage (`distroless`, `alpine` if appropriate)
- [ ] `USER` is non-root (drop from default UID 0)
- [ ] No secrets in layers (`docker history` reveals them)
- [ ] `HEALTHCHECK` defined
- [ ] No `apt-get install` without `apt-get clean` / `--no-install-recommends`
- [ ] `.dockerignore` excludes secrets, .env, .git

### Kubernetes

- [ ] `securityContext.runAsNonRoot: true`
- [ ] `securityContext.readOnlyRootFilesystem: true` (where compatible)
- [ ] `securityContext.capabilities.drop: [ALL]`, then add minimal needed
- [ ] `resources.limits` set (no unbounded memory/CPU)
- [ ] `livenessProbe`, `readinessProbe` defined
- [ ] No `hostNetwork`, `hostPID`, `hostIPC` unless justified
- [ ] Secrets via `Secret` resource (or external-secrets-operator), not env vars in manifest
- [ ] NetworkPolicy restricts pod-to-pod traffic (default-deny + explicit allows)
- [ ] PodSecurityAdmission `restricted` profile enforced

### GitHub Actions

- [ ] Workflows pinned to commit SHA, not tag (`uses: actions/checkout@<sha>` not `@v4`)
- [ ] `permissions: read-all` baseline; explicit per-job elevation
- [ ] No `pull_request_target` without careful review of fork attacks
- [ ] Secrets only in `secrets.X` references; never inline / printed
- [ ] Cloud auth via OIDC / WIF, not stored access keys
- [ ] No `set-output` (deprecated, leak-prone) — use `$GITHUB_OUTPUT`
- [ ] Branch protection requires status checks + review

## CI integration

```yaml
# .github/workflows/iac-scan.yml
on: [push, pull_request]
permissions:
  contents: read
  security-events: write
jobs:
  trivy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha>
      - uses: aquasecurity/trivy-action@<sha>
        with:
          scan-type: config
          scan-ref: .
          severity: HIGH,CRITICAL
          exit-code: 1
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@<sha>
        with:
          sarif_file: trivy-results.sarif
```

Critical/High findings break the build. Medium findings tracked but don't block.

## Suppression discipline

When you must suppress a finding:

```hcl
# trivy:ignore:AVD-AWS-0123 — Public bucket required for static asset CDN; restricted by CloudFront OAI
resource "aws_s3_bucket" "static" { ... }
```

Always include:

- The check ID being suppressed
- A one-line justification
- A pointer to the compensating control if any

Suppressions are reviewed quarterly. Stale ones get re-evaluated.

## Anti-patterns

- **Scanning at deploy time only.** PR-time prevents most issues
- **Wildcard suppressions** (`# trivy:ignore` without check ID). Permanent blind spots
- **No `prevent_destroy` on stateful resources.** One bad `terraform apply` away from data loss
- **Latest tags on images.** Untracked behavior change
- **Secrets in TF state.** State is sensitive; encrypt + restrict access
- **Cleartext secrets in K8s ConfigMap.** Use Secret + sealed-secrets / external-secrets

## See also

- `scanning-security` — orchestrates this in the broader gate
- `auditing-deps` — for application-level deps; this skill is infrastructure-level
- `CLAUDE.md` § Safety floor, item 5 (nothing reaches production outside the pipeline)
