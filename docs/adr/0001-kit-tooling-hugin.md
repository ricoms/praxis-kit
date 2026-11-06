# 0001 — The kit's tooling becomes one Python command, `hugin`, over adopted tools

- Status: accepted
- Date: 2026-11-06
- Deciders: architecture decider

## Context

The kit's tooling is five Python scripts, about 2,300 lines, using only the standard library: `scripts/profiles.py`,
`scripts/radar.py`, `scripts/check_template.py`, and the skill helpers `velocity.py` and `snapshot.py`.

- **No Python version is declared or provided.** `radar.py` imports `tomllib`, which needs Python 3.11, and macOS's
  own `/usr/bin/python3` is 3.9.6. A stopgap check in the justfile now fails with a clear message instead of a
  traceback, but every teammate still has to install a suitable interpreter by hand.
- **Several defects fixed in `snapshot.py` were shape errors** that a strict type checker reports: timestamps compared
  as strings, and a field list repeated by hand in places that drifted apart. Nothing in the kit runs a type checker
  on its scripts.
- **The tooling is expected to grow into a code-health tool** that supports the team's agreements and tracks code
  quality over time, alongside the repository snapshot and the delivery-velocity reading it already computes.

A spike measured the candidate engines on three repositories, and an open-source survey followed it:

- **Counting function complexity is cheap and conventional.** Rules written in about 40 minutes reproduced lizard on
  every function measured, and every engine ranked the same hotspots on non-test code. Each difference between
  engines came from a counting convention, such as whether `assert` or a closure counts, not from noise.
- **The long-lived tools are the healthy ones.** lizard, `tree-sitter`, `ast-grep` and Semgrep or Opengrep have
  several maintainers, steady releases and answered issues. The newer tools aimed at AI agents re-implement the same
  concepts, are mostly one person's work, and score risk with weights that nothing validates against real bug data.
- **What no tool does for the kit** is keep one output format with written conventions, ratchet a team against its
  own baseline, map logins to roles before anything is shared, and check a signal against the team's own history
  (bug labels, reverts, failed deploys) before calling it a risk.

An earlier draft of this record proposed moving the tooling to Rust. It is withdrawn. A thin layer over adopted tools
gains little from a compiled binary when some of those tools, such as lizard, run on Python themselves. A strict type
checker catches the shape errors that motivated it, and `uv` removes the interpreter drift.

## Decision

`hugin` is one Python package and command in this repository. It has two parts:

1. **The kit's own tooling**, which has no outside equivalent: the profile resolver and installer, the radar check,
   the template checks, the repository snapshot and its lineage queries, and the board's velocity reading. The
   existing scripts move into it.
2. **Thin adapters over adopted tools** for code analysis. Every adapter writes the kit's fixed output format, under
   conventions written in the repository, so a baseline survives a change of tool. The ratchet, the role mapping and
   the validation against the team's own history live in `hugin`, never in an adopted tool.

**Python and its typing.**

- `requires-python = ">=3.13,<3.15"`. The package uses the current typing features, such as PEP 695 type parameters,
  `typing.override`, `TypeIs` and `ReadOnly`.
- `mypy --strict` runs in `just check` and in CI as a gate on `hugin`. Code not yet moved in meets it as a ratchet,
  with today's errors as the baseline.

**Interpreter and dependencies.**

- `uv` runs `hugin` (`uv run hugin …`) from the justfile and from skills. It installs Python 3.13 itself when the
  machine lacks it, so teammates need `uv`, not a particular system Python. The kit already uses `uv` to run copier.
- The repository commits a `pyproject.toml` and a `uv.lock`. Every dependency has an upper bound and goes through the
  upgrade cooldown, under floor rule 2.
- The justfile's version stopgap is removed once `hugin` replaces the scripts.

**Adopting a tool.** A tool is adopted only when it passes all of these:

- it has commits in the last 12 months;
- more than one person merges changes;
- outside issues and pull requests get answers;
- it ships releases on a steady cadence that can be pinned;
- its licence lets the team use it and contribute to it, with no use restrictions such as BSL's. Copyleft code, such
  as AGPL or GPL, is called as a separate program, never imported into `hugin`.

`hugin` adds its own code only where no tool that passes does the job, and the record of that choice cites the
evidence. Each adoption is its own decision, taken when the job is built. These are the candidates for each job,
none adopted yet:

| Job | Candidates | How `hugin` would use it |
|---|---|---|
| Function complexity and smells | lizard; rules for `ast-grep` | lizard as a library; `ast-grep` through its Python bindings, `ast-grep-py`. The spike showed both reproduce the same scores |
| Duplication | `jscpd` | a separate program, through its JSON report |
| Line counts | `tokei`; `scc` | a separate program, through its JSON output |
| Reading git history | `git` itself | a separate program, as the snapshot already does |
| Visualisation | CodeCharta | `hugin` writes CodeCharta's import format instead of drawing its own charts |

**Contributing upstream.** A defect found in an adopted tool is reported to that tool's project, with a minimal
reproduction, and fixed there where the team can. The spike found such defects in lizard's Rust and TypeScript
readers.

**Scope.** `hugin` holds computation and checks. A step an agent performs by following a skill's instructions stays an
instruction; `hugin` does not replace it with a command.

## Consequences

- Teammates need `uv` to run the kit's tooling. A system Python no longer matters, and `uv` provides 3.13 on any
  machine.
- The kit gains dependencies where it had none. They fall under floor rule 2 and the weekly dependency audit like any
  project's. A tool adopted as a separate program, such as `jscpd`, which needs Node, or `tokei`, adds an install
  step; each adoption decision names it.
- A type checker finds shape errors when `just check` runs, not at compile time, and only in typed code. Strict mode
  and fixture tests close most of the gap that a compiler would.
- An adopted tool's limits become `hugin`'s. lizard's misreadings of Rust are an example. A list of known deviations
  per tool, and upstream fixes, keep those limits visible and shrinking.
- The Rust ports planned earlier are withdrawn, and the epic they belonged to is re-scoped to this decision.
- Python 3.13 is chosen for its typing features and its support window, which runs to October 2029. Most of CPython's
  recent speed gains arrived in 3.11 and 3.12, and `hugin`'s run time is dominated by git and the GitHub API, not by
  the interpreter.
