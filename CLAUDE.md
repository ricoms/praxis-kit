# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

The kit a team shares: `CONSTITUTION.md`, the team practices, agreements, decision points and references, plus the agent rules, skills and template that enforce them. It is installed via symlinks (not copies) into `~/.claude/` or a project's `.claude/`. Editing a file here changes it everywhere it's symlinked. There is no app to build or run — the "product" is the documents, the `claude/` tree, `template/`, and the kit's tooling in `src/hugin/`, including the profile resolver (`hugin profiles`).

Nothing specific to one person belongs here. A person's own tooling lives in their own kit, installed on top with `hugin profiles --kit` (see `CONSTITUTION.md` §6). Before adding an artifact, ask whether a team member needs it to follow a shared agreement; if not, it belongs in a personal kit.

## Commands

```sh
just list-profiles              # profiles + descriptions
just resolve PROFILE             # merged artifact set after extends chain
just validate                    # every artifact claimed by >=1 profile, agent tool grants cover what their skill invokes, description length lint
just check-template              # render template variants, actionlint + shellcheck, ruleset vs ci.yml, practices and constitution claims
just test                        # fixture tests for the kit's scripts (scripts/tests)
just typecheck                   # mypy --strict: a gate on src/hugin, a ratchet on unmoved scripts (scripts/mypy-baseline.txt)
just check                       # everything CI runs, in order: validate, budget, radar check, test, typecheck, check-template; run before every push
just budget                      # always-on byte total (CLAUDE.md + rules + skill frontmatter descriptions) vs BUDGET_LIMIT ratchet in src/hugin/profiles.py
just doctor                      # two-way drift: repo artifacts vs installed ~/.claude tree
just install                     # symlink all profiles into ~/.claude/
just install-only minimal security
just install-project DIR PROFILE...
just clean-stale [ROOT]          # remove symlinks pointing at removed artifacts of this repo, or of the kit at ROOT
just status                      # what's currently symlinked in ~/.claude/
just references-fetch           # download the arXiv sources behind docs/references/*.md (PDFs are gitignored)
just docs-index                  # index CONSTITUTION.md, docs/references and docs/ai-sdlc as the qmd collection praxis-kit
```

CI (`.github/workflows/ci.yml`) runs `validate`, `budget`, the radar check, `test`, `typecheck` and `check-template` on every push/PR to `main`; `just check` runs the same six locally. Every recipe runs Python through `uv run`, which provides 3.13 from the root `pyproject.toml` and `uv.lock`.

`hugin` (ADR 0001, `docs/adr/0001-kit-tooling-hugin.md`) is the kit's Python package, in `src/hugin/`, run as `uv run hugin`. The scripts under `scripts/` and `claude/skills/*/scripts/` move into it one at a time; until each moves, `just typecheck` holds its `mypy --strict` errors to the baseline. `scripts/tests` holds the fixture tests for `hugin`'s commands.

Manual `resolve`/single-artifact checks: `uv run hugin profiles <command>` directly (`--help` lists every command). `uv run hugin profiles --kit DIR <command>` runs any command against another kit with the same `profiles/` + `claude/` layout, such as a personal kit installed on top of this one; only this repo installs `CLAUDE.md` and `CONSTITUTION.md`.

## Architecture

### Profile resolution (`hugin profiles`, `src/hugin/profiles.py`)

Each `profiles/*.json` declares `description`, optional single-level `extends`, and up to five kinds of artifact lists: `skills`, `agents`, `commands`, `rules`, `assets`. `resolve()` walks the `extends` chain and merges lists (later/child entries append, de-duped). `install()`/`install-project()` symlink the merged set from `claude/<kind>/<item>` into the target's `.claude/<kind>/`, and always link `claude/CLAUDE.md` and the root `CONSTITUTION.md` into `.claude/`. Existing local non-symlink files at the target are preserved and reported as `SKIP`, never overwritten.

Every profile except `minimal` extends it directly or transitively — `minimal` carries the always-on rules and the skills every team project uses (clarification, issues and boards, project docs, instruction files). `base` adds the security scan gate that pairs with the template; `security`, `spec-kit` and `team-delivery` extend `base`.

### Always-on budget

`claude/CLAUDE.md` + everything under `claude/rules/` (recursive, no `@`-import needed) + every skill's frontmatter `description` gets loaded into every session regardless of profile. `just budget` sums that footprint against a ratchet limit (`BUDGET_LIMIT` in `src/hugin/profiles.py`) that only ever decreases. Adding an always-on rule or lengthening a skill description must displace bytes elsewhere — reference-heavy material belongs in an on-demand skill's body or sibling reference file, never in `rules/` or a description string.

### Skills vs rules vs agents vs commands

- `claude/rules/` — always-on, no invocation needed. Reserve for cross-cutting, load-bearing constraints (tenancy glossary, OWASP API checklist, secrets lifecycle, clarify protocol cadence, issue labelling). Anything here is paid for in every session.
- `claude/skills/<name>/SKILL.md` — on-demand, invoked by name or trigger description. Progressive disclosure: SKILL.md stays under ~500 lines; heavy reference content (regex corpora, pricing tables, persona defs, runbooks) lives in sibling files loaded only when the skill pulls them in.
- `claude/agents/*.md` — subagent definitions with their own tool grants (the `tools:` frontmatter). This kit ships none; a kit installed on top with `--kit` may. `just validate` checks that an agent's grant covers every tool its skill declares in `allowed-tools` or `metadata.requires-tools`, plus a few it detects in the skill's text, such as `Agent(` and `AskUserQuestion`. `allowed-tools` is what Claude Code pre-approves without a prompt; `requires-tools`, under `metadata:`, is everything else the skill needs, such as a write a developer still approves per-call. A tool the skill only describes in prose is not detected, so the skill must declare it in one of the two fields.
- `claude/commands/*.md` — slash command entry points, usually thin wrappers that invoke a skill or agent.

### Editing an artifact

Skills/agents/rules/commands are referenced by exact filename/dirname in one or more `profiles/*.json`. After adding, renaming, or removing an artifact under `claude/`, update every profile that lists it and run `just validate` — an artifact claimed by zero profiles fails validation, and a profile referencing a missing artifact fails silently at install time (`MISS` in `install`'s output) rather than erroring.

### Authoring conventions (enforced by `authoring-instruction-files` skill)

- Every rule/skill/command declares the altitude it operates at; skills document *when* to trigger, not just *what* they do.
- Tenancy mode (`multi-tenant` | `single-tenant` | `single-user`) is per-consuming-project, declared in that project's own `CLAUDE.md`, never assumed here — this repo has no tenancy model itself, it only encodes the rule that other projects must declare one.
- No invented terminology, no theory citations in the artifact body (background-only), comments-in-code rules apply recursively to this repo's own shell/Python scripts.

### `copier.yml` and `template/` — copier scaffold

Separate from the profile system: a [copier](https://copier.readthedocs.io/) template, whose `copier.yml` sits at the repo root so copier can version it, with the delivery machinery every project shares (workflows with slots for the stack, process files, runbooks, the practices' scripts). It chooses no language, database or cloud; a stack template fills the slots. Not installed via `install.sh`.

## Constraint: nothing identifying

The kit is public. No client, employer or person names in tracked files or commit messages, and examples stay
fictional. `CONTRIBUTING.md` holds the full contributor rules.
