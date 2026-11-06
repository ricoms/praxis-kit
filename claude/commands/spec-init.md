---
description: Initialize spec-kit in the current project with a constitution copied from the kit's root for the project's stage
allowed-tools: Bash(specify *) Bash(cp *) Bash(mkdir *) Bash(test *) Bash(grep *) Bash(awk *) Bash(git *) Read Write Edit AskUserQuestion
---

# /spec-init

Initialize [spec-kit](https://github.com/github/spec-kit) in the current project and fill its constitution from the kit's root, for the stage and tenancy mode the project declares. Idempotent — safe to re-run.

## Steps

1. **Verify spec-kit is installed**:

   ```sh
   specify --version
   ```

   If not installed: `uv tool install specify-cli` and retry.

2. **Initialize `.specify/` if missing**:

   ```sh
   test -d .specify || specify init
   ```

   `specify init` is non-destructive — re-running it on an existing tree won't clobber.

3. **Fill the project constitution** by following `bootstrapping-with-spec-kit` step 3 exactly:
   read the stage and tenancy mode from `.claude/CLAUDE.md` (ask if either is missing), copy the skeleton from
   `~/.claude/spec-kit/constitution.md`, fill every `[COPY ...]` slot word for word from the named source, keep
   only the active practices' gate rows, and run the copy check until it prints nothing.

4. **List the gaps** under Governance: every gate that says "review", and any safety-floor rule the project cannot
   meet yet, each with an owner and a date. Ask the user for owners with `AskUserQuestion`, one question at a time.

5. **Commit**:

   ```sh
   git add .specify/memory/constitution.md
   git commit -m "chore: adopt the project constitution for stage <stage>"
   ```

   Add the `Assisted-by:` trailer for the model actually running.

6. **Suggest next step**:

   > Constitution adopted. Run `/speckit.specify "<feature>"` to begin the first spec-driven feature.

## Notes

- This command does NOT replace `/speckit.*` — those continue to work normally. This command only handles the bootstrap step
- If `.specify/memory/constitution.md` already exists, ask the user before overwriting (use `AskUserQuestion`: keep existing / overwrite / merge / abort)
- The copied sections are never edited in the project; copy them again when the stage, the tenancy mode or the root changes. A different stack changes only the gate column (`deriving-a-constitution.md`)

## See also

- `bootstrapping-with-spec-kit` skill — full procedure and amendment guidance
- `~/.claude/spec-kit/constitution.md` — the skeleton
- `~/.claude/CONSTITUTION.md` — the source of the copied sections
