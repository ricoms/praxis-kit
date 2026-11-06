---
name: authoring-instruction-files
description: >-
  Author agent instruction files (kernel, rules/, skills): progressive
  disclosure, right altitude, residency test. Use when creating or editing a
  rule, skill, or CLAUDE.md, or auditing instructions for bloat.
metadata:
  tags:
    - context-engineering
    - meta
    - instruction-authoring
---

# Authoring Instruction Files

The always-on layer is an **attention budget, not free space**. Recall degrades as context grows (context rot, measured across 18+ frontier models), and instruction-following tops out well below 100% as rule count rises (~68% at 500 simultaneous instructions, IFScale). So a buried rule isn't inert — it lowers the odds the important rules fire. Author for signal density, not coverage.

## Multi-level progressive disclosure

Three tiers — keep each tier thin and push detail down:

1. **Always-on** — name + description (skills) / the resident rule body. The "should I engage this?" signal. Costs every session.
2. **On-trigger** — SKILL.md body / a `paths:`-scoped rule. Loads when the task matches.
3. **On-demand** — bundled `reference.md` / `runbooks.md` / examples the body tells the agent to open. Costs nothing until read.

Default move when a file gets fat: **leave a one-line pointer in the higher tier, move the body down.** Markdown `##` headings + the agent's own grep are the index — don't hand-maintain a table of contents.

## Right altitude

Aim for the **minimal phrasing that fully specifies the behavior**. Both extremes are defects:
- **Too low** — brittle, over-specified logic / exhaustive caveats → fragile, high-maintenance, dilutes attention.
- **Too high** — vague guidance with no concrete signal, or assumes shared context the model lacks.

## Residency test (always-on vs on-demand)

Keep a rule in the always-on tier only if it scores high on **at least one**:
1. **Frequency** — bears on a large share of *actual* sessions (not one unrepresentative session).
2. **Marginal value of residency** — encodes *your custom policy* the model wouldn't default to; not generic knowledge it already has.
3. **Failure cost** — silent non-firing is dangerous (security / compliance / data-integrity guardrails earn residency even when infrequent).

Scores low on all three → demote to a skill or `paths:`-scoped rule.

## Charter discipline

If a file declares "detail lives elsewhere," enforce it — audit for drift. A kernel that points elsewhere for setup detail but still carries the stack table has bloated against its own rule. Dedup to the pointer.

## Project CLAUDE.md (global vs. project split)

Same residency test, one level down: global `CLAUDE.md` carries portfolio-wide defaults and policy; project `CLAUDE.md` carries the resolved, repo-specific facts that would otherwise force every session in that repo to re-derive them — tenancy mode and stage (each verbatim, with a one-line reason), the stack actually in use (state it even when it matches global defaults; a deviation from the global stack gets its own line), and anything else specific to that repo.

Location: root `CLAUDE.md`, not `.claude/CLAUDE.md` — matches actual practice across the portfolio.

New project → the shared template renders it with the tenancy mode and stage; fill its Stack section. Existing repo with none yet → same content spec, retrofitted: read the repo's actual package manifests before asking, and don't restate global rules the repo doesn't deviate from.

## Claude Code mechanics (verify before relying)

- `~/.claude/rules/**` auto-loads recursively at launch — `@`-importing a file already under `rules/` is dead config.
- `paths:` frontmatter scopes a rule to matching files, but is documented only for **project-level** `.claude/rules/` — don't rely on it for global guardrails.
- Verify what loaded with `/memory`; debug with the `InstructionsLoaded` hook.
- `allowed-tools` lists the tools Claude Code runs without a prompt, so a safe skill pre-approves only reading. List every other tool the skill uses in `requires-tools` under `metadata:`, including a write the developer approves per call and `Agent` when the skill starts subagents. Prose such as "start a fresh agent" is invisible to `just validate`, which fails an agent that follows the skill without a tool either field declares. A scoped agent grant such as `Bash(git *)` does not satisfy `Bash`; grant the full tool.

## Sources

ThoughtWorks Radar Vol. 34 *Context engineering* (Adopt), *Agent instruction bloat* (Hold), *Progressive context disclosure* (Trial) · Anthropic *Effective context engineering for AI agents* · IFScale (arXiv 2507.11538) · Chroma *Context Rot* · Liu et al. *Lost in the Middle*.
