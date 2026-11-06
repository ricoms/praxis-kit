---
name: reading-delivery-velocity
description: >-
  Board velocity: estimate done per sprint vs capacity, margin to a milestone,
  actual ÷ estimate by phase. Use at sprint end, a capacity check, or before
  re-estimating.
metadata:
  tags:
    - delivery
    - planning
---

# Reading delivery velocity

Reads a GitHub project board set up by the team kit (`template/` with `team_delivery`: sprints are milestones;
Estimate, Actual, Remaining Work, Waiting and Phase are fields; Status Done means closed). Read-only.

## Run it

```sh
uv run --no-dev --project <kit> hugin velocity --owner <org> --project <n> \
  --capacity <engineer-days per sprint> --target "<milestone>"
```

`<kit>` is the praxis-kit checkout this skill is linked from: the resolved path of this skill's directory, three levels
up. `uv` provides Python 3.13 there. Field names, the done status and today's date are flags (`--help`).
`--input items.json` reads a saved `gh project item-list <n> --owner <org> --format json --limit 5000` instead of
calling `gh`.

`snapshotting-repositories` calls the same functions, through `hugin snapshot`, to store a board reading with each
snapshot.
`scripts/tests/test_velocity.py` pins the printed reading.

## Read it

- **Done ÷ capacity per sprint** above 100% means the sprint closed more estimate than planned capacity; below it,
  carry-over or missing estimates. Check which before calling it a slip.
- **Margin** is capacity left to the target milestone minus open work (Remaining Work, else Estimate). Negative means
  re-plan or re-scope now, not at the milestone.
- **Actual ÷ estimate by phase** is what re-weights the next estimates (team practices Article VIII): multiply a new
  phase estimate by its ratio. Rows marked *small sample* (fewer than 5 pairs) are hints, not corrections.
- **Coverage** below most of the done work means the ratios describe a subset; fix the board first
  (`docs/runbooks/board.md`): each closed issue needs its Actual.

Actual is days of work and Waiting is days blocked; the script never adds them. Waiting is decision latency, read
separately.

## Post the reading

Only when the owner asks: paste the output as a comment on the checkpoint issue, with the command line used, so the
next reading can be compared.
