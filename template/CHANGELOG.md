# Template Changelog

## No private-reference check (2026-11-06)

The template stops rendering `scripts/private-refs.sh`, `.github/private-refs.txt` and CI's `private-refs` job. The
hand-over runbook searches for the team's private names with `git grep` instead. On a team, run
`scripts/repo/apply-ruleset.sh` after the update so the ruleset stops requiring `private-refs`; no PR can merge while
a required check never reports, so an admin applies it from the update branch before merging it.

## Less process automation (2026-11-06)

The template stops rendering automation that policed how people work:

- the door check: `.github/workflows/doors.yml`, `.github/scripts/doors.py`, `doors.sh` and `.github/doors.toml`;
- the board close-out: `.github/workflows/close-out.yml` and `.github/scripts/close-out.sh`;
- the daily digest: `.github/workflows/digest.yml` and `.github/scripts/digest.sh`;
- `.github/team-delivery.env`, which only those scripts read;
- `scripts/security-scope.py` and the `security-scope` recipe.

The agreements stay. The author labels a one-way change `door:one-way` and requests a review, the assignee records
Actual and Remaining Work when an issue closes, and a security test's scope is listed from the API contract. The
`door:two-way` label goes too, because nothing applies it; the labels workflow does not delete labels, so run
`gh label delete door:two-way --yes`.

An update deletes the files above, including any the project edited. To keep one, restore it with
`git checkout HEAD -- <path>` before committing the update. The
`PROJECT_OWNER` and `PROJECT_NUMBER` variables and the `PROJECT_TOKEN` and `SLACK_WEBHOOK_URL` secrets have no reader
any more: delete them, and revoke the token and the Slack webhook.

## CI grows with the stack (2026-11-06)

A new question, `stack_decided`, says whether the project's stack is decided. Until it is true, CI renders only the
checks that need no stack, so a fresh render passes CI on its first push. It defaults to true past `explore` or with
`release_workflow`, which requires it. `just ci` now follows the stage: `explore` runs `test` only.
`README.md` § How CI grows describes the steps.

The ADR lint is gone: `scripts/adr-lint.sh`, CI's `adr` job and its required status check. Every ADR still states its
Status and Deciders, by agreement. The image and smoke scripts and `.github/smoke.txt` render only with
`release_workflow`, which is the only thing that calls them. On a team, run `scripts/repo/apply-ruleset.sh` after the
update so the ruleset stops requiring `adr`.

A project rendered earlier in `build`, `run` or `sustain`, or with `release_workflow`, keeps its `checks` job on
update. A project in `explore` without `release_workflow` whose slots are filled passes `--data stack_decided=true`
on its next update. Without it, the update removes CI's `checks` job. With `team_delivery`, the ruleset still requires
`checks` until `scripts/repo/apply-ruleset.sh` runs, and no PR can merge while a required check never reports, so
an admin applies the new ruleset from the update branch before merging it.

## Rename to praxis-kit (2026-11-06)

The kit was published as praxis-kit. A project rendered under its earlier name, setup-aiad, renames
`.copier-answers.setup-aiad.yml` to `.copier-answers.praxis-kit.yml` once and sets its `_src_path` to
`https://github.com/ricoms/praxis-kit.git`.

## v0.1 — initial scaffold (2026-05-22)

The first scaffold rendered a backend and frontend stack. That stack moved out to separate stack templates, and this
template now renders only the delivery machinery every project shares; `template/README.md` § What it produces lists
it.
