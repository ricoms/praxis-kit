# Agent rules

These rules load in every session, for every project. The root is `CONSTITUTION.md` in the same `.claude` directory: values, safety floor, stages and agreements between people. It wins over this file. Resolve its relative links from the checkout named by `kit` in `~/.claude/.kit-manifests/praxis-kit.json`. A project's own `CLAUDE.md` declares its tenancy mode, stage and stack, and extends this file.

When two goals conflict, rank them: Security > Compliance > Testing > Usability > Performance > Simplicity.

## Safety floor (NON-NEGOTIABLE)

These hold at every stage, in every codebase. Constitution §2.

1. **Secrets are never committed**, including in history and test fixtures. Lifecycle: `rules/security/secrets-lifecycle.md`.
2. **Every dependency is locked and upper-bounded.** No open `>=`, lockfiles are committed, and images are referenced by digest. Pinning syntax, tiers and cooldown: `auditing-deps`.
3. **Nothing merges while checks are red.** Never bypass, skip or weaken a check to make it pass.
4. **Data access is scoped by the declared tenancy mode.** See `## Tenancy`.
5. **Nothing reaches production outside the pipeline.** Never run a manual `terraform apply`, `kubectl` or cloud CLI change against a shared environment, not even for a quick fix.

## Tenancy

A project declares `multi-tenant`, `single-tenant` or `single-user`. Definitions and identifier names are in `rules/glossary.md`. If the mode is missing, ask before generating code that assumes scoping. Never pick one for the user.

## Stage

A project declares `explore`, `build`, `run` or `sustain`. The stage decides which practices are on, per the table in constitution §4. New code meets an active practice as a gate. Existing code meets it as a ratchet: a recorded baseline that only shrinks. Never raise a threshold to make a check pass. If the stage is missing, ask before applying a stage-dependent practice.

## How agents work

- **Verify before calling work done.** Run the project's lint and test recipes, read the full diff, then check imports, module boundaries, types, test meaning, security and i18n. Update `tasks.md` if the project has one.
- **Verify the path, not the piece.** A green test on a function says nothing about whether anything calls it. A check counts only once it has been seen failing with the defect present.
- **A default indistinguishable from a real answer is a silent failure.** A fallback fixture, a stub returning `[]` or an unread value reports success it did not earn. Fail closed at the boundary, and make an unreachable path raise.
- **Eliminate a defect rather than detect it.** If one line makes the bad state unrepresentable, prefer it to a guard with its tests and wiring. Do not write a wrapper that adds nothing over the call it fronts.
- **Normalize input that can be fixed without loss**, such as by trimming or canonicalizing, at the one shared boundary. Fail loudly only on what normalizing cannot repair. Untrusted input stays deny-by-default.
- **When code deduplicates or compares values a unique key will check, compare them as the store holding that key does**: its case, width, accent and ignorable-character rules. Otherwise let the store compare, for example with an upsert. A batch or paged write sets aside a row that breaks a key, so one row cannot fail the batch or stall the cursor.
- **Check maintenance before recommending a dependency**: commits within 12 months and responsive issues. Never call one "battle-tested" or "well-maintained" without checking. Prefer official, then foundation, then active community packages, then minimal inline code.
- **Assert structure in tests of prompts and user-facing copy**, not exact wording: inputs appear in the output, sections are counted, lengths fall in a range.
- **Flag uncertainty rather than guess.** Say what was not checked.

## Code comments

Comment only non-obvious runtime behavior. Never narrate the change; rationale goes in the commit or PR. Prose never outweighs the code it describes. A docstring past about three lines, or any incident narrative, belongs in the ADR or issue. A declaration (field, column, constant, parameter) gets no comment; if it seems to need one, rename it.

## Accountability and attribution

- A human reads the full diff and takes responsibility for it. An agent never adds `Signed-off-by` or claims authorship.
- AI-assisted commits carry `Assisted-by: AGENT:MODEL [tools]`, naming the model actually running. Omit the version if it is unknown. List only the analysis and verification tools used.
- AI-written code meets the same quality bar as human code.
- An agent never messages another person or changes an external account without being asked.

## Where the rest lives

- Security: `rules/security/owasp-api-top-10.md` for every API change. Threat models: `threat-modeling`. Multi-tenant LLM features: `isolating-multi-tenant-llm`.
- Specifications: spec-kit (`.specify/`, `specs/`) when the stage requires a spec.
- A malicious dependency: `responding-to-supply-chain-compromise`.
