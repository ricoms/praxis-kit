# Secrets Lifecycle

Always-on. Applies to every secret (API keys, DB credentials, signing keys, OAuth secrets, encryption keys, webhook secrets). Rotation runbooks: `skills/rotating-secrets`.

- **Issue**: per-environment, per-service/purpose. Short-lived creds when possible (STS, WIF, OIDC for CI). Generated, never human-rememberable (`openssl rand -base64 32`)
- **Store**: Secret Manager / Vault / sealed-secrets — never committed `.env` (leaks via stash/amend/diff even gitignored), never plain ConfigMap, never TF state. Per-secret IAM + read audit logs
- **Use**: loaded at process start, not per-request. Never in logs (redact secret-shaped fields), never in URLs (Authorization header), never in client-side code
- **Rotate**: 90 days prod / 30 days high-risk / immediately on compromise. Test in staging first; log each rotation in `docs/runbooks/rotations.log`. Auto-rotate what you can (TLS via cert-manager, KMS keys)
- **Revoke**: on suspected compromise revoke FIRST, investigate after. Employee departure → automated, <24h. Vendor breach → rotate keys held with that vendor even if not named. Post-revoke: search logs for use of the revoked secret — use after revocation means something was missed
- **Detect**: gitleaks pre-commit + server-side secret scanning on every push + vendor breach notifications subscribed

**Compromise response**: revoke → issue new + roll consumers → search logs for post-issuance use → search IOCs → audit everything the secret could access → document in `docs/runbooks/incidents/YYYY-MM-DD-<id>.md` → post-mortem the leak vector.

**Anti-patterns**: long-lived keys where WIF/OIDC/STS works; one secret shared across services; rotation as the *only* defense; manual rotation of what could auto-rotate.
