# Contributing

praxis-kit changes through pull requests to `main`. This page says what a pull request needs, and how the parts of
the kit that hold agreements change differently from the rest.

## Before you open a pull request

- **Run `just check`.** It runs the same six checks as CI (see [README § Checks](README.md#checks)), and nothing
  merges while one is red. Never weaken or skip a check to make it pass.
- **Keep one change per pull request, based on `main`.** Don't stack a pull request on another one that hasn't merged.
- **Write Conventional Commits,** such as `fix(skills): …` or `docs: …`, with the reason for the change in the body.
- **Open an issue first** for anything larger than a fix, using one of the issue forms. One question goes in one
  issue.

## Changes that need agreement

- **[`CONSTITUTION.md`](CONSTITUTION.md)** changes only by amendment, as its section 7 describes: the pull request
  states which velocity signal or part of the safety floor it serves, with evidence, and stays open for an objection
  window before the named decider merges it.
- **[`docs/ai-sdlc/practices.md`](docs/ai-sdlc/practices.md)** applies the constitution and must not contradict
  it. A pull request that changes what an article asks of a team gives its evidence, as the articles do, and one that
  would contradict the constitution needs the amendment first. A fix to wording or a broken link is an ordinary pull
  request.

## Agent rules and skills

- Anything under [`claude/rules/`](claude/rules/), the kernel [`claude/CLAUDE.md`](claude/CLAUDE.md), and every
  skill's `description` load into every session. `just budget` holds their total under a limit that only goes down,
  so adding bytes there means removing bytes elsewhere.
- A skill keeps its `SKILL.md` short and puts reference material in sibling files. The
  `authoring-instruction-files` skill describes the conventions.
- A new or renamed skill, rule or command is listed in a profile under [`profiles/`](profiles/); `just validate`
  fails otherwise.

## Nothing identifying

The kit is public. Tracked files and commit messages name no client, employer or person, and examples use fictional
companies, domains and dates. A pull request that needs a real engagement as evidence summarises it with rounded
figures, as [`docs/ai-sdlc/evidence.md`](docs/ai-sdlc/evidence.md) does.

## AI-assisted contributions

AI-assisted work is welcome, under the same rules the kit gives its own agents:

- A person reads the full diff and takes responsibility for it. An agent never adds `Signed-off-by` or claims
  authorship.
- An AI-assisted commit carries an `Assisted-by: AGENT:MODEL [tools]` trailer, naming the model that actually ran and
  only the analysis and verification tools used.
- AI-written code meets the same bar as any other code.

## Reporting a vulnerability

Don't open a public issue. See [`SECURITY.md`](SECURITY.md).

## Licence

By contributing, you agree that your contribution is licensed under the repository's [MIT licence](LICENSE).
