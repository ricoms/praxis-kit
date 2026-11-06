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

## The backstop: the set cannot shrink quietly

Scenarios carry a `foundational` tag. A recipe writes the list of tagged scenarios to a committed manifest; CI
regenerates it and fails on any difference, so removing, renaming or un-tagging one needs a manifest change in the
same diff, where review sees it. A pending, skipped or todo scenario warns on a PR and fails on `main`.

| Stack | Manifest | Pending on `main` fails when |
|---|---|---|
| pytest | `pytest -m foundational --collect-only -q \| grep '::' \| sort` | `pytest -m foundational -q -rsx \| grep -E '^(SKIPPED\|XFAIL)'` finds a line |
| RSpec | `rspec --tag foundational --dry-run --format json \| jq -r '.examples[] \| "\(.file_path) \(.full_description)"' \| sort` | `rspec --tag foundational --format json \| jq -e '.summary.pending_count == 0'` is false |
| Vitest | name files `*.foundational.test.ts`; `vitest list .foundational.test. --json \| jq -r '.[] \| "\(.file) \(.name)"' \| sort` | `vitest run .foundational.test. --reporter=json --outputFile=f.json`, then any status other than `passed`/`failed` in `f.json` |

pytest needs the marker registered (`markers = ["foundational: …"]`) and `--strict-markers`, so a typo in the tag
fails instead of silently selecting nothing. `vitest list` leaves out `.todo` tests; the pending check still catches
them. RSpec descriptions, not positional ids, keep the manifest stable when examples are reordered.

```just
foundational-check:
    <manifest command> > tests/foundational_manifest.txt
    git diff --exit-code -- tests/foundational_manifest.txt
```

Run the pending check with `continue-on-error: ${{ github.event_name == 'pull_request' }}` so it warns on PRs and
fails on `main`.

## Evidence

One rebuild ([evidence](../evidence.md#repository-and-checks)): developers wrote and maintained the
contract themselves; the tagged suite caught real regressions; the pending backstop
was added after pending scenarios could reach `main`. No case was found of the manifest diff catching erosion — its
value is that a removal cannot happen out of sight.
