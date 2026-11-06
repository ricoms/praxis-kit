# praxis-kit

praxis-kit is a shared kit for a software delivery team whose developers work with
[Claude Code](https://claude.ai/code) agents. It is written for a team that builds software someone else will own,
often a vendor building for a client who inherits the repository. A team building its own product can use it too and
skip the client-facing parts, which the template makes optional.

The problem it addresses: without written agreements, each developer and each agent follows its own unspoken
conventions, and that is where friction, blame and surprises come from. praxis-kit writes the agreements down once
and installs them where the agents read them.

It gives the team three things:

- **Written agreements:** a constitution with values, a safety floor and stages, and team practices for how work
  moves from plan to release.
- **Agent rules and skills** that install into Claude Code, so every agent session follows the agreements and can run
  the procedures that enforce them.
- **A [copier](https://copier.readthedocs.io/) template** that adds the delivery machinery to a project: CI workflows,
  labels, issue forms and runbooks.

**The entry point is one command.** Install the kit, open your project in Claude Code, and run
`/settling-agreements`. It reads what the project already does, proposes the project's agreements, and asks only about
the gaps. You approve the result as a pull request.

The practices come from one such engagement, reviewed three times without changing anything, from mid-delivery to its
close.
[`docs/ai-sdlc/evidence.md`](docs/ai-sdlc/evidence.md) summarises what was measured; the research behind it is
private. Terms used throughout are explained under [Terms](#terms).

## Start here

1. Check the [prerequisites](#prerequisites), then clone the kit and work from inside the checkout, where every `just`
   recipe runs: `git clone https://github.com/ricoms/praxis-kit.git && cd praxis-kit`.
2. Install the kit's rules and skills (see [Install](#install)).
   - `just install-only minimal` installs into `~/.claude`, so the rules load in every Claude Code session on the
     machine. Add profiles from the table under Install as you need them, or run `just install` for all of them.
   - To leave the rest of the machine untouched, `just install-project /path/to/project minimal` installs into that
     project's `.claude/` only.
   - A `CLAUDE.md` already at the target that is not one of the kit's links is left alone and reported as `SKIP`.
     The kit's rules then do not load there until you move that file aside or merge it.
3. Open your project in Claude Code and run `/settling-agreements`. It reads what the project already does, starts from
   any `agreements.md` you bring from another project or your team, and asks only what it cannot work out.
4. Approve the resulting `docs/agreements.md`. A team reads it as a PR first, then meets only on the rows someone contests.

**Starting a new project?** Apply the [template](template/README.md) before step 3. It renders `.claude/CLAUDE.md` and
`docs/agreements.md`, and copier overwrites both, so anything settled earlier is lost. The rendered
`.claude/CLAUDE.md` extends the global `~/.claude/CLAUDE.md`, so a project made from the template needs the global
install. Run `just install-project` into it after `copier copy`, never before: copier will not write over the files the
install links.

**Want the background first?** Skim [`CONSTITUTION.md`](CONSTITUTION.md): what the team is after, the safety floor,
the stages and the agreements that `/settling-agreements` settles.

## What is here

| Layer | What it holds | Where |
|---|---|---|
| Constitution | values, the safety floor, stages, the agreements between people | [`CONSTITUTION.md`](CONSTITUTION.md) |
| Practices | how each practice is done in a team project, with what enforces it | [`docs/ai-sdlc/practices.md`](docs/ai-sdlc/practices.md), [`docs/ai-driven-lifecycle.md`](docs/ai-driven-lifecycle.md) |
| Defaults | stack and tool choices, each with alternatives | [`docs/ai-sdlc/decision-points.md`](docs/ai-sdlc/decision-points.md), [`docs/ai-sdlc/radar.md`](docs/ai-sdlc/radar.md), [`template/`](template/) |
| Evidence | what the practices were measured against, and notes on the papers behind them | [`docs/ai-sdlc/evidence.md`](docs/ai-sdlc/evidence.md), [`docs/references/`](docs/references/) |
| Agent rules | what every agent session loads | [`claude/CLAUDE.md`](claude/CLAUDE.md), [`claude/rules/`](claude/rules/) |
| Skills | the procedures the practices name as enforcement | [`claude/skills/`](claude/skills/), with the commands that start them |
| Distribution | how the kit is installed and checked | [`profiles/`](profiles/), [`src/hugin/`](src/hugin/), [`scripts/`](scripts/), [`justfile`](justfile) |

Nothing here is specific to one person. A person's own tooling lives in their own kit, installed on top (see
[Personal and organisation kits](#personal-and-organisation-kits)).

## Prerequisites

- [Claude Code](https://claude.ai/code), which loads the kit's rules and skills.
- git, [`uv`](https://docs.astral.sh/uv/) and [`just`](https://github.com/casey/just). `uv` provides Python 3.13 when
  the machine lacks it.
- The [GitHub CLI](https://cli.github.com/), `gh`, signed in. Several skills read and file issues and pull requests
  through it.
- For the template: [`copier`](https://copier.readthedocs.io/) and a GitHub repository. With the template's
  `team_delivery` option, also a GitHub Projects board for the team.
- To run the kit's own checks: `actionlint`, `shellcheck` and Docker for `just check-template`, and
  [qmd](https://github.com/tobi/qmd) for `just docs-index`.

## Install

The kit's tooling runs through [`uv`](https://docs.astral.sh/uv/), which provides Python 3.13 itself when the machine
lacks it, so the system Python does not matter. `hugin`, the kit's command (ADR 0001,
`docs/adr/0001-kit-tooling-hugin.md`), runs as `uv run hugin`, and its tests run with `uv run python`. The
project-registry recipes also run with `uv run python`; set `PYTHON` to run them with another interpreter instead.

Files are **symlinked**, not copied, from this repository into `~/.claude/` or a project's `.claude/`. Editing a file
here changes it everywhere it is linked. A local file that is not a symlink is never overwritten.

```sh
just install                                   # every profile into ~/.claude, plus CLAUDE.md and CONSTITUTION.md
just install-only minimal security
just install-project /path/to/repo security team-delivery
just status                                    # what is linked now
just doctor                                    # drift between this repo and ~/.claude
just clean-stale                               # remove links to artifacts this repo no longer has
just projects-sync-all                         # re-apply profiles to the projects listed in projects.json (gitignored;
                                               # start from projects.example.json)
```

| Profile | Holds |
|---|---|
| `minimal` | the always-on rules and the skills every team project uses: clarification, settling agreements, issues and boards, project docs, instruction files |
| `base` | the security scan gate that pairs with the template (extends `minimal`) |
| `security` | dependency audit, IaC scanning, threat models, data classification, abuse scenarios, secrets rotation, supply-chain incident response, API and multi-tenant LLM review (extends `base`) |
| `spec-kit` | spec-driven development with a project constitution copied from the root for the project's stage and tenancy (extends `base`) |
| `team-delivery` | a multi-developer team with agents: work loop, next actions, board, review of delivered work, threat models, specs, docs, velocity, repository snapshots, verifying the path; pairs with the template's `team_delivery` (extends `base`) |

To start a new project from the template, see [`template/README.md`](template/README.md).

## Checks

CI runs these six on every push and pull request to `main`, and `just check` runs the same six locally:

```sh
just validate             # every artifact belongs to a profile; agent tool grants cover their skills; spec-kit gates cover every practice
just budget               # always-on bytes (kernel + rules + skill descriptions) against BUDGET_LIMIT, a ratchet that only goes down
uv run hugin radar check  # each radar entry's backing file still says what the entry claims
just test                 # fixture tests for hugin's commands, under scripts/tests
just typecheck            # mypy --strict on src/hugin, as a gate
just check-template       # renders the template's variants and checks what the practices claim about it
```

## Personal and organisation kits

A person's or an organisation's own kit sits on top of this one ([constitution §6](CONSTITUTION.md#6-where-everything-else-lives)).
It has the same `profiles/` + `claude/` layout and is installed with this repository's installer:

```sh
uv run --no-dev --project ../praxis-kit hugin profiles --root ../praxis-kit --kit ../my-kit install
```

It never installs `CLAUDE.md` or `CONSTITUTION.md`, and an item name this kit already links is reported `TAKEN`
instead of replaced. `just clean-stale ../my-kit` removes dangling links into it.

## Terms

| Term | Meaning |
|---|---|
| Kernel | [`claude/CLAUDE.md`](claude/CLAUDE.md), the agent rules installed as `~/.claude/CLAUDE.md` and loaded in every session. With [`claude/rules/`](claude/rules/), it is the kit's always-on context. |
| Always-on budget | The bytes the kernel, the rules and every skill's description add to each session. `just budget` holds them under a limit that only goes down. |
| Profile | A named set of skills, rules and commands in [`profiles/`](profiles/). An install picks one or more profiles. |
| Skill | A procedure an agent loads when it is asked for by name or when its description matches the task, under [`claude/skills/`](claude/skills/). |
| Stage | `explore`, `build`, `run` or `sustain`. A project declares one, and the stage decides which practices are on ([constitution §4](CONSTITUTION.md#4-stages)). |
| Tenancy mode | `multi-tenant`, `single-tenant` or `single-user`. A project declares one, and it decides how data access is scoped ([glossary](claude/rules/glossary.md)). |
| Gate and ratchet | New code must meet a practice before it merges: a gate. Existing code records today's shortfall once as a baseline that may only shrink: a ratchet ([constitution §3](CONSTITUTION.md#3-gates-and-ratchets)). |
| One-way and two-way door | A change is one-way when reverting it after release may not restore an equivalent state, and two-way when a revert and redeploy does. The author labels a one-way pull request `door:one-way` ([constitution §5](CONSTITUTION.md#5-agreements-between-us)). |
| Slot | A recipe, script, action, repository variable or API contract the project fills for its stack. The template's workflows call slots, and an unfilled slot fails loudly ([template README](template/README.md#the-slots-a-project-fills)). |
| Board fields | Estimate, Actual, Remaining Work, Waiting and Phase: fields on the team's GitHub Projects board, defined in the board runbook the template renders. |
| Radar | [`docs/ai-sdlc/radar.md`](docs/ai-sdlc/radar.md): the kit's tool and practice choices, each linked to a file that backs it. A check fails when that file stops saying so. |
| ADR | Architecture decision record: one file per decision under `docs/adr/`, with its status and who decided. |
| RACI | Who is Responsible, Accountable, Consulted and Informed for each type of decision ([practices, Article IV](docs/ai-sdlc/practices.md#iv-raci-by-decision-type)). |
| Door classifier | A script that labels each pull request one-way or two-way from the paths it changes. The evidence in `docs/ai-sdlc/evidence.md` was measured with one; the template does not ship it. |
| Engagement ledger | A private record, kept outside the repository, of who was told what and when, and of open requests to people outside the team ([decision points](docs/ai-sdlc/decision-points.md)). |
| AI-SDLC | AI-assisted software development lifecycle, the name of the [`docs/ai-sdlc/`](docs/ai-sdlc/) folder that holds the practices. |
| hugin | The kit's command-line tool, run as `uv run hugin`. It renders and checks the radar and reads delivery velocity ([ADR 0001](docs/adr/0001-kit-tooling-hugin.md)). |
| spec-kit | GitHub's [spec-driven development toolkit](https://github.com/github/spec-kit). The `spec-kit` profile wraps it and copies the constitution into a project. |

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Report vulnerabilities privately, as [`SECURITY.md`](SECURITY.md)
describes.

## License

MIT
