---
name: writing-tests
description: >-
  Tests by tier: Gherkin scenarios, component tests, structural checks;
  frozen foundational tests. Use when planning, writing or reviewing tests.
metadata:
  tags:
    - testing
    - bdd
    - tdd
---

# Writing tests

`CONSTITUTION.md` §4 asks for tests at the right tier: scenarios for cross-module flows, component tests for modules,
and structural checks. In `explore`, one smoke check stands in for all three. This skill is the method for writing
them, in any stack. It applies when planning a feature's tests, writing them, or reviewing someone else's.

A test verifies behaviour through a public interface, never the implementation behind it. The implementation can
change entirely, and a good test does not notice.

## Pick the tier

| Tier | What it checks | When it is written | Example tools |
|---|---|---|---|
| Scenario | A flow across modules, or a behaviour a user sees, in Gherkin | Before the implementation, from the spec | behave or pytest-bdd (Python), Cucumber (JVM, Ruby, JavaScript), playwright-bdd (browser), godog (Go) |
| Component | One module through its public interface, with only the external systems it calls replaced | Test-first, one slice at a time | pytest, Vitest or Jest, RSpec, JUnit, `go test`, `cargo test` |
| Structural | Types, lint, complexity and module boundaries | Configured once, run on every change | mypy or pyright, Ruff, `tsc`, ESLint, clippy, import-linter, dependency-cruiser |

The tools are examples, not requirements. The project's stack decides them, and its `justfile` runs them through
`just test` and `just lint`.

Most tests are component tests. Scenarios are few: each one is a behaviour whose failure means the feature failed.
A detail that a component test can check stays out of the scenarios, so they stay readable and fast enough to run on
every change.

## Scenarios in Gherkin

A scenario is a piece of the spec that runs. Write it in the domain's language, as what the user achieves, never as
which buttons they press.

```gherkin
Feature: Checkout

  Scenario: A customer pays for a cart within their credit limit
    Given a customer with a credit limit of 100 EUR
    And a cart holding items worth 80 EUR
    When the customer checks out
    Then the order is confirmed
    And the customer's remaining credit is 20 EUR
```

- One behaviour per scenario. `Given` sets the state, `When` is one action, and `Then` is an outcome someone can
  observe.
- Use concrete values. When the same rule holds for several values, use a `Scenario Outline` with an `Examples`
  table instead of copying the scenario.
- Use `Background` only for state that every scenario in the file needs.
- Step definitions are thin glue. Each one calls the system's public interface, never its internals, and keeps no
  logic of its own. A `Then` step holds the comparison, so for a foundational scenario it is frozen with the scenario.
- Run a new scenario before implementing it, and watch it fail for the right reason: the behaviour is missing, not a
  step is undefined.

When a spec drives the feature, its acceptance scenarios are these scenarios. Draft each one in the spec as a
fenced `gherkin` block. When the spec is approved, the person approving it saves the blocks as feature files under
`tests/foundational/` and writes or approves their `Then` steps. An agent drafts but never saves them there: that
approval is what freezes them. The spec then links to the files instead of restating them.

## Component tests, test-first

Work in vertical slices: one test, then the code that makes it pass, then the next test. Writing every test first
and every piece of code afterwards tests imagined behaviour, and it fixes the test structure before the design is
understood.

1. **Red.** Write one test for the next behaviour, through the module's public interface, and watch it fail.
2. **Green.** Write the least code that makes it pass.
3. **Refactor**, only while green. Remove duplication, and move complexity behind a smaller interface. Run the tests
   after each step.

Replace only the external systems the module calls: an external API, the clock, randomness, and sometimes the
filesystem or a database that is too slow to start. Never replace the module's own collaborators.
[good-tests.md](good-tests.md) shows good and bad tests and how to design for this.

## Structural checks

The strictest type checking and lint the language offers, a complexity limit, and checks that modules depend only on
each other's public interfaces. They are on from `build` (§4). New code meets them as a gate. Existing code records
its shortfall once, as a baseline that may only shrink.

## Frozen foundational tests

A foundational test checks behaviour whose failure means the delivery failed. Its expected value is set before the
implementation exists, by someone other than the implementer, from the spec or from the system being replaced. Team
practices Article IX and `docs/ai-sdlc/patterns/foundational-contract.md` explain why.

- Foundational tests live in their own folder, `tests/foundational/`, with everything that states or checks an
  expected value: feature files, their `Then` step definitions and the modules that load them, or plain test files
  whose assertions are the contract. `Given` and `When` steps and fixtures live outside it and change freely. Each
  runner's configuration names the folder.
- **An agent never edits, moves or deletes a file in that folder.** The project's `.claude/settings.json` stops Claude
  Code's editing tools and the shell commands it recognises, but not `rm` or `mv`, so this rule holds either way. If a
  frozen test looks wrong, stop and tell the person you act for. Its owner changes it. The deny rule applies only to a
  session started at the repository root, so start Claude Code there.
- A person may change one. On a team, the CODEOWNERS line for the folder requests the decision owners' review.
- A pending or skipped foundational test never reaches `main`.

## When test-first is the wrong tool

- **A spike.** Write throwaway code without tests, then delete it before writing the real thing test-first.
- **A visual change.** Tests cannot see that something looks wrong. Pair a few snapshot tests with a person looking.
- **A migration.** Test the outcome, such as the data after the run, not the migration's own logic.
- **A bug.** Reproduce it as a failing test first, then fix it.

## Per test

- It describes a behaviour, not an implementation step.
- It uses only the public interface, and would survive a refactor that keeps the behaviour.
- The code it drove in is the least that makes it pass.

---

Adapted from [mattpocock/skills `tdd`](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd) (MIT licence, notice in
[LICENSE-mattpocock.txt](LICENSE-mattpocock.txt)). [good-tests.md](good-tests.md) has the same provenance.
