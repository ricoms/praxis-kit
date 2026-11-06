# Shared delivery template

A copier template for the delivery machinery a team shares: the GitHub workflows, process files, runbooks and
scripts that apply the team practices (`../docs/ai-sdlc/practices.md`). Its `copier.yml` sits at the repository root,
because copier versions a template only from the root of a git repository. It chooses no language, database or cloud.
Where a workflow needs the stack, it calls a slot the project fills, and an unfilled slot fails loudly instead of
passing.

## Usage

```bash
uvx copier copy --trust https://github.com/ricoms/praxis-kit.git ./my-new-project
uvx copier copy --trust --defaults --data-file answers.yml https://github.com/ricoms/praxis-kit.git ./my-new-project
cd my-new-project && git init && git add -A && git commit -m "Render the praxis-kit template"
uvx copier update --trust --answers-file .copier-answers.praxis-kit.yml
```

`answers.yml` holds the answers to the questions in [`copier.yml`](../copier.yml), one `name: value` line each.

`copier update` runs only in a git repository whose changes are all committed, so commit the rendered project before
the first update.

The source is the praxis-kit repository's git URL. The answers file records it, and every update resolves it from
there, so anyone with read access to the kit can update the project. A local checkout path would be recorded as
given, and the update would then work only on the machine that has it.

The answers go to `.copier-answers.praxis-kit.yml`, so a stack template applied afterwards can keep its own answers
file; every update names it with `--answers-file`. praxis-kit has no release tags yet, so an update takes the latest
commit; once tags exist, it takes the latest tag. To change an answer later, such as turning on `release_workflow`,
pass `--data release_workflow=true` to the update.

## Hand-over

With `team_delivery`, the rendered project carries `docs/runbooks/hand-over.md`: the checklist for everything the
team does when the repository passes to the client, from deleting the answers file through retiring the team's own
board and secrets to moving access last, each step with how to verify it.

## What it produces

The files this template renders into a project are licensed [MIT-0](LICENSE-MIT-0) (MIT No Attribution), so a
rendered project owes no notice for them.

- `.claude/CLAUDE.md` with the declared tenancy mode and stage, and sections for the stack, modules and flows.
- `.copier-answers.praxis-kit.yml`, the answers and template commit that `copier update` starts from.
- `docs/agreements.md`, the ten decisions every team settles, with proposed defaults; `docs/slo.md`, `docs/adr/`,
  and the runbooks: CI/CD troubleshooting, the runbook index, incidents, `rotations.log`.
- `.github/workflows/ci.yml`: `checks` runs `just ci` after the toolchain action, `image` builds with
  `scripts/build-image.sh` and smoke-checks the image, plus the ADR lint and gitleaks.
- `justfile` with the recipe contract (`ci`, `lint`, `test`, `audit`, `secrets`, `security-scan`, `smoke`), and a stack-free
  two-stage `.pre-commit-config.yaml` and `dependabot.yml`.
- With `release_workflow`: `.github/workflows/release.yml` (build once, deploy to dev on a pre-release, promote the
  same digest to prod, roll back through the pipeline) and `docs/runbooks/rollback.md`.
- With `team_delivery`: labels, the issue forms (bug, enhancement, question, client question, decision, risk and
  security test, each applying a kind label), board close-out and the daily digest,
  the door check, CODEOWNERS, the PR template, a `main` ruleset with its apply script, the private-reference check,
  `docs/raci.md`, and the board, review-and-merge, security-testing and hand-over runbooks.

## The slots a project fills

| Slot | Called by | What it does |
|---|---|---|
| `.github/actions/toolchain` | CI's `checks` job | Installs the stack's tools; `just` is already there |
| `just lint`, `just test`, `just audit` | `just ci` | The project's static checks, tests and dependency audits |
| `scripts/build-image.sh TAG` | CI's `image` job, the release's `build` job | Builds the deployable image, which must listen on `$PORT` and answer `GET /health` |
| `IMAGE_REPOSITORY` repo variable | `release.yml` | Where images are pushed |
| `.github/actions/target-setup` | `release.yml` | Logs in to the registry and the target, from repository variables |
| `scripts/deploy.sh current\|release\|revert` | `release.yml` | Reports what serves an environment, deploys an image by digest, routes traffic back |
| `scripts/migrate.sh ENV` (optional) | `release.yml` | Forward-only migration before a release, never on a rollback |
| `openapi.json` (or `API_CONTRACT`) | `just security-scope` | The API contract a security test's scope is generated from |

A stack that fills these slots can live in its own template and be applied after this one.
