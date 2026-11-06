# Per-Secret-Type Rotation Runbooks

## Contents

- [AWS access keys (IAM user)](#aws-access-keys-iam-user)
- [GCP service account key](#gcp-service-account-key)
- [Anthropic / OpenAI / Google AI API keys](#anthropic-openai-google-ai-api-keys)
- [Database password (Postgres / MySQL / MongoDB)](#database-password-postgres-mysql-mongodb)
- [JWT signing key](#jwt-signing-key)
- [OAuth client secrets](#oauth-client-secrets)
- [Webhook signing secrets (Stripe, Twilio, GitHub, etc.)](#webhook-signing-secrets-stripe-twilio-github-etc)
- [TLS certificates](#tls-certificates)
- [Encryption-at-rest keys (KMS / CMEK)](#encryption-at-rest-keys-kms-cmek)

Companion to `SKILL.md`. Each runbook follows the universal procedure (issue → propagate → verify → revoke → audit) with type-specific commands. The secret custodian runs them, elevated for the rotation only; an agent fills them in for the issue and never runs them.

## AWS access keys (IAM user)

```bash
# 1. Create new key
aws iam create-access-key --user-name <user>

# 2. Update the secret store and CI secrets with the new key (don't delete old yet)
# 3. Roll services that use it
# 4. Verify (CloudWatch, app logs)
# 5. Disable old key (soft revoke, allows quick rollback)
aws iam update-access-key --user-name <user> --access-key-id <old> --status Inactive

# 6. Wait 24h (catch any forgotten consumer)
# 7. Delete old key
aws iam delete-access-key --user-name <user> --access-key-id <old>
```

**Better than rotation: eliminate access keys.** Use IAM Roles + IRSA (EKS) / IAM Roles for Tasks (ECS) / WIF (Cloud Run / GKE) / OIDC (GitHub Actions). Rotation becomes automatic.

## GCP service account key

```bash
# Avoid creating these in the first place — use Workload Identity Federation.
# If you must rotate one:
gcloud iam service-accounts keys create new-key.json --iam-account=<sa-email>

# Distribute new-key.json, restart consumers
# Then disable the old:
gcloud iam service-accounts keys disable <KEY_ID> --iam-account=<sa-email>

# Wait, then delete:
gcloud iam service-accounts keys delete <KEY_ID> --iam-account=<sa-email>
```

## Anthropic / OpenAI / Google AI API keys

1. Console → API keys → create new
2. Update secret store
3. Roll consumers
4. Console → API keys → delete old
5. Audit usage logs (Anthropic console / OpenAI dashboard) for the old key — anything after revocation = forensics

LLM provider keys often power high-cost paths. Set per-key cost caps if available (Anthropic: workspaces; OpenAI: project keys).

## Database password (Postgres / MySQL / MongoDB)

Two options:

**(A) Dual-credential window (zero downtime)**: create a new user, grant identical privileges, switch consumers, drop old user.

```sql
-- Postgres
CREATE USER app_user_v2 WITH PASSWORD :new_password;
GRANT <same privileges> TO app_user_v2;
-- Switch app config to app_user_v2 / new_password
-- Verify, then:
DROP USER app_user;
```

**(B) Same-user password rotation**: change password, restart all consumers near-simultaneously.

```sql
ALTER USER app_user WITH PASSWORD :new_password;
-- Restart all consumers
```

(A) is safer; (B) is simpler if downtime is acceptable.

## JWT signing key

JWT rotation needs a key-rollover window because in-flight tokens are still valid:

1. Issue new key, give it a `kid` (key ID)
2. Configure verifier to **accept both old and new** for the rollover window
3. Configure issuer to **sign only with new**
4. Wait for the old key's max-token-age to elapse (e.g., 24h if tokens last 24h)
5. Remove old key from verifier acceptance
6. Delete old key

JWKS endpoint makes this clean — clients fetch the key set, no client redeploy needed.

## OAuth client secrets

```
1. Provider console → Add new client secret (don't delete old)
2. Distribute new secret
3. Roll consumers
4. Wait — provider often shows "last used" timestamp on each secret
5. Delete old when "last used" is well in the past
```

## Webhook signing secrets (Stripe, Twilio, GitHub, etc.)

1. Provider console → rotate secret (some support multiple active secrets, allowing rollover)
2. Update consumer config to verify against the new secret (or both during overlap)
3. Watch for verification-failure spikes — those are unrolled consumers
4. Once stable, disable the old secret in the provider

## TLS certificates

Modern: use ACME / cert-manager / Let's Encrypt for auto-rotation. If you must rotate manually:

1. Generate new key + CSR
2. Get cert
3. Deploy new cert + key to load balancer (zero-downtime if your LB supports cert reload)
4. Verify cert chain serves correctly (`openssl s_client -connect host:443 -servername host`)
5. Old cert expires; nothing to revoke unless compromise

If compromise: revoke via OCSP / CRL provider in addition to deploying the new cert.

## Encryption-at-rest keys (KMS / CMEK)

Most cloud KMS supports key rotation natively (AWS KMS rotates yearly; GCP Cloud KMS configurable). For application-layer keys:

1. Generate new data key
2. Re-encrypt data with new key (lazy on next write, or batch backfill)
3. Verify new key in use
4. Mark old key as disabled (still usable for decrypt of old ciphertext)
5. After full backfill, schedule old-key destruction (per regulator's data-retention rules)
