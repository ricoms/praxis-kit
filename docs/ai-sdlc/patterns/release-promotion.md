# Release promotion

Team practices Article XIII. A decision point: the template ships one default; pick another when the client's stack
already has, or needs, what it offers.

The settled shape holds for every option: images are pushed only by releases; a pre-release builds once and runs in
dev; marking it final promotes the same digest to prod; a release that skipped the pre-release builds once and goes
to prod, saying so; each environment's database is migrated right before it gets the version.

## Default — GitHub deployment records (template `release.yml`)

GitHub Actions does the promotion itself. The image for a commit is tagged with the commit SHA in an Artifact
Registry repository with **immutable tags**, so the tag always names the image built and tested for that commit. The
deploy job is the one job bound to the GitHub environment, so each run leaves one deployment record; marking a release
final promotes only when the commit's latest `dev` deployment succeeded, and stops otherwise.

Pick it when: the team lives in GitHub, there are one or two environments, and nothing else orchestrates releases.
Costs nothing beyond Actions minutes. The promotion logic is ours to maintain (tested by `hugin check-template`).

## Option — Google Cloud Deploy

A managed delivery pipeline with targets (dev → prod). The release workflow creates a Cloud Deploy *release* from the
pushed digest on a pre-release and calls `gcloud deploy releases promote` when it is marked final; Cloud Deploy
promotes the same release to the next target without rebuilding.

- **Verification** runs your check containers after each deploy; on Cloud Run they run in Cloud Deploy's execution
  environment, and a failing verification fails the rollout.
- **Repair rollout** automation retries a failed rollout and, when retries are exhausted, rolls back to the most
  recent successful release on that target.
- Optional approvals, scheduled promotions, and a console with each release's rollout history per target.
- Pricing: single-target pipelines are free; the first active multi-target pipeline per billing account is free; each
  additional one is $5 a month, plus the underlying services.

Pick it when: the client already uses Cloud Deploy, there are more than two environments or canary rollouts, or
operators want release history outside GitHub. It replaces the template's `plan` decision, rollback step and
deployment-record check; the build-once job and the smoke checks (as a verify container) stay.

Not shipped by the template yet: wiring it means a `clouddeploy.yaml` (pipeline and targets), a Skaffold config for
Cloud Run, and the deployer role `roles/clouddeploy.releaser`.

## Option — signed attestations

Sign each release image (GitHub artifact attestations) and have prod admit only images carrying a dev-passed
attestation (Binary Authorization on Cloud Run). The strongest guarantee that prod runs what dev verified, at the cost
of attestor setup and a policy to maintain. Not evaluated in depth here; consider it when supply-chain requirements
call for signed provenance.

## Sources

- [Cloud Deploy: promote a release](https://docs.cloud.google.com/deploy/docs/promote-release)
- [Cloud Deploy: verify your deployment](https://docs.cloud.google.com/deploy/docs/verify-deployment)
- [Cloud Deploy: automation](https://docs.cloud.google.com/deploy/docs/automation)
- [Cloud Deploy pricing](https://cloud.google.com/deploy/pricing)
