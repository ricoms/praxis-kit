# Foundational test contract

Team practices Article IX. A pattern, not template code: the recipes below are per stack.

## What it guards against

An agent writes an implementation and its test in the same change, then adjusts the expected value until the test
passes. The test now proves the code agrees with itself, and nothing about the behaviour it was meant to preserve.
No reviewer recovers an expected value that was never established independently.

## The control: who writes the scenario, and when

A **foundational scenario** is behaviour whose failure means the delivery failed. Its expected value is fixed
**before the implementation exists**, by **someone other than the implementer**, from a source the code cannot be
tuned against:

- a rebuild or migration: behaviour observed on the old system (a harness run, recorded traffic, a demo);
- greenfield: acceptance criteria agreed with the client in the spec.

Before writing any, mark each candidate *preserve* or *do-not-preserve*. A contract drawn from everything the old
system does will guard behaviour the new spec removes on purpose.

This part is process. No check enforces it; the PR that adds a scenario should show it predates the implementation.

## The backstop: the folder is frozen

Foundational tests live in their own folder, `tests/foundational/`. Everything that states or checks an expected value
lives there: Gherkin feature files with their `Then` step definitions, and the modules that load them, such as
pytest-bdd's `scenarios(...)`; or plain test files whose assertions are the contract. `Given` and `When` step
definitions and fixtures drive the system without judging it, so they live outside and change freely. Each runner's
configuration names the folder, for example Cucumber's `paths` and `import`, playwright-bdd's `features` and `steps`,
or Cucumber-JVM's `cucumber.features`. Two controls guard the folder, and neither is a CI check:

- **Agents cannot change it.** The project's `.claude/settings.json`, which the template renders, holds the deny rule
  `Edit(./tests/foundational/**)`. It covers Claude Code's edit, write and notebook tools, and the shell commands it
  recognises, such as `sed`, `tee` and `>` redirection. It holds in every permission mode, and no allow rule can
  override it. The project's `.claude/CLAUDE.md` also tells agents never to edit, move or delete a file there.
- **People can, visibly.** On a team, `.github/CODEOWNERS` requests the decision owners' review on every PR that
  touches the folder or `.claude/settings.json`. Removing or renaming a test, or changing an expected value, shows as
  a change in that folder. The review is a request, as every review is by default; a team that wants it required
  turns on `require_code_owner_review` in its ruleset.

The freeze has edges, and review covers them rather than more checks:

- The deny rule applies only to a session started at the repository root. A session started in a subfolder does not
  load the root's `.claude/settings.json`, so the `CLAUDE.md` rule is all that holds there.
- It does not stop a shell `rm` or `mv`, or a script that opens a file itself.
- The runner configuration, and the `Given` and `When` steps and fixtures, sit outside the folder. Changing them can
  skip a frozen test or fake the state a frozen `Then` reads, and each such change shows in the diff.

A pending, skipped or todo foundational test warns on a PR and fails on `main`:

| Stack | Pending on `main` fails when |
|---|---|
| pytest | `pytest tests/foundational -q -rsx` exits 5 because it collected no test, or its output has a `SKIPPED` or `XFAIL` line |
| RSpec | `rspec tests/foundational --format json \| jq -e '.summary.example_count > 0 and .summary.pending_count == 0'` is false |
| Vitest | `vitest run tests/foundational --reporter=json --outputFile=f.json`, then any status other than `passed`/`failed` in `f.json` |

Cucumber fails on pending or undefined steps when run with `--strict`. Run the check with
`continue-on-error: ${{ github.event_name == 'pull_request' }}` so it warns on PRs and fails on `main`.

## Evidence

One rebuild ([evidence](../evidence.md#repository-and-checks)): developers wrote and maintained the contract
themselves; the tagged suite caught real regressions; the pending backstop was added after pending scenarios could
reach `main`. The manifest of names it used then caught no erosion, and it could not see an edited expected value,
which is why the folder is frozen instead.
