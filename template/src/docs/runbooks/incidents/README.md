# Incident postmortems

One file per production incident: `YYYY-MM-DD-<short-id>.md`. Blameless — the point is fixing the
system, not assigning fault.

## Required sections

- **Impact** — who/what was affected, for how long
- **Trigger** — the immediate event that started it
- **Detection** — how it was noticed (alert? user report? nothing, until this postmortem?) — a slow
  detection is itself a finding
- **Timeline** — timestamped, from trigger to resolution
- **Root cause(s)** — plural on purpose; incidents usually have more than one contributing factor

## Action items

Action items become GitHub issues, **linked from this doc** — never checkboxes written directly
here. A checkbox in a postmortem is an action item nobody's tracking; an issue is.
