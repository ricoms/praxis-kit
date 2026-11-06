---
name: bootstrapping-with-spec-kit
description: >-
  Bootstrap spec-kit with a constitution copied from the root for the
  project's stage and tenancy. Use once a project declares both, for
  non-trivial projects, or to retrofit spec-kit.
metadata:
  tags:
    - spec-driven
    - spec-kit
    - bootstrapping
    - constitution
---

# Bootstrapping with Spec-Kit

[spec-kit](https://github.com/github/spec-kit) drives spec-driven development: constitution → specify → clarify → plan → tasks → analyze → implement → checklist. The project constitution makes its phase gates enforce the safety floor and the practices the project's stage switches on (`~/.claude/CONSTITUTION.md` §4).

## Prerequisites

- `uv` installed (Python tool installer)
- A git repo whose `.claude/CLAUDE.md` declares a tenancy mode and a stage (the shared template renders both). If either is missing, ask before going on
- `~/.claude/CONSTITUTION.md` installed (`just install` in praxis-kit)

## Steps

Copy this checklist into your response and tick off as you progress:

```
Bootstrap Progress:
- [ ] Step 1: Install spec-kit (uv tool install specify-cli)
- [ ] Step 2: Initialize .specify/ (specify init)
- [ ] Step 3: Fill the constitution from the skeleton, copying word for word, then run the copy check (or /spec-init)
- [ ] Step 4: List the gaps under Governance, then commit
- [ ] Step 5: Begin first feature (/speckit.specify "<feature>")
```

### 1. Install spec-kit

```sh
uv tool install specify-cli
specify --version
```

(One-time per machine.)

### 2. Initialize `.specify/`

```sh
specify init
```

Creates `.specify/` with default templates. The skill runs in the current project root.

### 3. Fill the constitution from the skeleton

```sh
cp ~/.claude/spec-kit/constitution.md .specify/memory/constitution.md
```

Fill `.specify/memory/constitution.md`:

- Replace `[PROJECT_NAME]`, `[STAGE]`, `[TENANCY]` and `[DATE]`. For `[COMMIT]`, run the command below; it fails if `~/.claude/CONSTITUTION.md` is not the installed symlink, and marks a checkout with uncommitted changes `-dirty`:

  ```sh
  src=$(readlink ~/.claude/CONSTITUTION.md) && git -C "$(dirname "$src")" describe --always --dirty
  ```
- Replace each `[COPY ...]` line with the text it names, **copied word for word with its line breaks**. Never summarise or reword: the check below fails on any line that is not in the source.
- In the phase-gate table, keep only the rows for the practices you copied.

Then run the copy check with the project's stage and tenancy mode. It prints nothing when every slot is filled, every
copied line is exact, and the right lines were copied: the five floor rules, the declared tenancy row, and as many
practice rows as the stage switches on.

```sh
f=.specify/memory/constitution.md stage=build tenancy=single-tenant c=~/.claude/CONSTITUTION.md
grep -n '\[COPY\|\[LIST\|\[STAGE\]\|\[TENANCY\]\|\[DATE\]\|\[COMMIT\]\|\[PROJECT_NAME\]' "$f"
[ "$(grep -c '^<!-- copy: ' "$f")" = 4 ] || echo "expected 4 copy blocks"
awk '/<!-- copy: /{src=$3; next} /<!-- end copy -->/{src=""; next} src != "" && NF {print src "\t" $0}' "$f" |
  while IFS="$(printf '\t')" read -r src line; do
    grep -qxF -- "$line" ~/.claude/"$src" || echo "not in $src: $line"
  done
[ "$(grep -c '^[1-5]\. \*\*' "$f")" = 5 ] || echo "expected the 5 floor rules"
grep -q "^| \`$tenancy\` |" "$f" || echo "missing the $tenancy row"
col=$(awk -F'|' -v s="$stage" '/^\| Practice \| explore/{for (i=1;i<=NF;i++) if ($i ~ " "s" ") print i; exit}' "$c")
want=$(awk -F'|' -v k="$col" '/^\| Practice \| explore/{t=1;next} t&&/^\|---/{next} t&&/^\|/{if ($k !~ /—/) n++; next} t{exit} END{print n}' "$c")
have=$(grep -cxF -f <(awk '/^\| Practice \| explore/{t=1;next} t&&/^\|/{print;next} t{exit}' "$c") "$f")
[ "$have" = "$((want + 1))" ] || echo "expected $want practice rows for $stage, found $((have - 1))"
```

(Or invoke `/spec-init`, which runs steps 2 to 4.)

### 4. List the gaps, then commit

Under Governance, list every gate that says "review" and any safety-floor rule the project cannot meet yet, each with an owner and a date.

**If the project's stack or layout is not the kit's** (a client's Laravel app, an inherited Django monolith), the copied sections still apply unchanged; only the gate column changes. Method in [deriving-a-constitution.md](deriving-a-constitution.md).

```sh
git add .specify/memory/constitution.md
git commit -m "chore: adopt the project constitution for stage <stage>"
```

Copy again whenever the stage or the tenancy mode changes, or the root changes.

### 5. Begin spec-driven flow

From here, use the standard spec-kit slash commands:

```
/speckit.specify "Add a new <feature>"
/speckit.clarify
/speckit.plan
/speckit.tasks
/speckit.analyze
/speckit.implement
/speckit.checklist
```

Each phase reads `.specify/memory/constitution.md` and checks proposed artifacts against its phase gates. Breaches of the safety floor or an active practice surface as Critical findings in `/speckit.analyze`.

## When to use spec-kit (and when not)

**Use** for: new features, multi-week initiatives, anything touching auth/payments/PII, anything multi-concept, refactors >5 files, anything where the design isn't obvious.

**Skip** for: typo fixes, dep upgrades (use `auditing-deps`), bug fixes, trivial CRUD additions to existing concepts.

From stage `build`, `CONSTITUTION.md` §4 requires a specification before a non-trivial feature — interpret "non-trivial" generously. The cost of running clarify + plan is small; the cost of skipping it on something that needed it is large.

## Per-project deviations

The copied sections are never edited in the project. A project that cannot meet a practice records it as a gap under Governance, with an owner and a date. A different stack or tool is an ADR, and changes only the gate column.

## Troubleshooting

- **`specify init` fails** — confirm `uv tool install specify-cli` succeeded; run `specify --version`
- **Slash commands not recognized** — they're loaded from `.specify/templates/commands/`; confirm the directory exists and the project root is the cwd in your editor
- **Analyze phase passes everything trivially** — the constitution may not be loading, or its gates name checks the project does not have; confirm the file exists and each gate names a real command
- **Constitution conflicts with spec-kit's default templates** — that's expected for project-specific overrides; place overrides in `.specify/templates/overrides/`

## See also

- `template/` in praxis-kit — renders `.claude/CLAUDE.md` with the tenancy mode and stage this skill reads
- `clarifying-with-user` — pairs with `/speckit.clarify` (same protocol; native command takes precedence inside spec-kit projects)
- `classifying-data` — Specify gate: what data the feature touches, and the retention / logging obligations that follow
- `writing-abuse-scenarios` — Specify gate: what someone tries that the feature was not built for. Cheaper than a threat model and it catches requirements functional specs never produce
- `threat-modeling` — invoked when a security-trigger feature reaches plan phase
- [deriving-a-constitution.md](deriving-a-constitution.md) — rewriting the gate column for a stack or layout that is not the kit's
- spec-kit upstream docs: <https://github.com/github/spec-kit>
- `~/.claude/CONSTITUTION.md` §2–§4 — the source of every copied section
