# Template Changelog

## CI grows with the stack (2026-11-06)

A new question, `stack_decided`, says whether the project's stack is decided. Until it is true, CI renders only the
checks that need no stack, so a fresh render passes CI on its first push. It defaults to true past `explore` or with
`release_workflow`, which requires it. `just ci` now follows the stage: `explore` runs `test` only.
`README.md` § How CI grows describes the steps.

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
