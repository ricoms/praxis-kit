---
name: clarifying-with-user
description: >-
  Structured clarification session: one question at a time via
  AskUserQuestion, atomic update per answer, cap 5. Use for vague requests,
  draft stress-tests, or /clarify.
metadata:
  tags:
    - interaction
    - clarification
    - spec-driven
---

# Clarifying with User

Structured ambiguity-reduction session. Wraps the global clarify protocol (`~/.claude/rules/interaction/clarify-protocol.md`) into an explicit invokable workflow.

Use when:

- The user's request is too vague to plan (e.g., "build a dashboard")
- A draft spec, plan, or ADR has gaps before implementation can begin
- Another skill (e.g., `bootstrapping-with-spec-kit`, `threat-modeling`) detects ambiguity in phase 1
- The user explicitly invokes `/clarify`

## Inputs

- The artifact to clarify: a spec file, plan, issue, draft message, or just a free-text request the user typed
- Optional: a target document to update atomically (default: append `## Clarifications` section to the artifact, or create `clarifications.md` next to it if the artifact isn't a writable file)

## Architecture

**Hybrid: subagent for heavy thinking, parent for Q&A loop.** Subagents (Agent tool) cannot drive interactive Q&A — they return a single result. So:

| Phase | Owner | Why |
|---|---|---|
| 1. Inventory | Subagent (Explore or general-purpose) | Reads artifact, scores 9 categories, returns top 5 questions as a queue. Heavy reading stays out of parent context |
| 2. Q&A loop | Parent | Uses `AskUserQuestion` per the protocol. One question at a time. Atomic update after each answer |
| 3. Synthesis | Subagent | Reads the answers log, returns the summary. Synthesis prose stays out of parent context |

Parent context only carries: the resolved Q–A pairs and the final summary. The exploratory reading and the synthesis prose live in subagent contexts.

## Workflow

### Phase 1 — Inventory (subagent)

Spawn an Explore-style subagent with this brief:

> Read `<artifact-path>`. Score clarification questions across the 9-category taxonomy (functional scope, data model, UX, non-functional, integration, edge cases, constraints, terminology, completion signals). Return the top 5 highest-impact questions as a JSON list:
> ```json
> [
>   {"category": "...", "impact": "would block ...", "question": "...", "options": [{"label": "...", "description": "..."}, ...], "recommended": "<label of recommended option, or null>"}
> ]
> ```
> Each question should have 2–4 options when possible (so it can render via AskUserQuestion); leave `options: []` for pure free-form questions. Do not ask the user. Do not exceed 5 questions. Skip trivia.

Receive the queue. Do **not** show the queue to the user — the protocol is one question at a time.

### Phase 2 — Q&A loop (parent)

For each question in the queue:

1. If `options` has 2–4 entries: call `AskUserQuestion` with one question. Use `(Recommended)` suffix on the recommended option's label
2. If `options` is empty: use the suggested-answer format (below)
3. Wait for the answer
4. **Atomically update the target document**: append `## Clarifications` section if absent, then `- Q: <question> → A: <answer>` line. Save before moving on
5. If the answer reveals a new higher-impact gap, requeue (still respecting the cap of 5 *asked*, not *queued*)

Stop conditions:

- Queue empty
- 5 questions asked
- User says "stop" / "enough" / "skip"

### Phase 3 — Synthesis (subagent)

Spawn a subagent with this brief:

> Read `<answers-log-path>`. Generate a summary in this format:
> ```
> ## Resolved
> - Q: ... → A: ...
>
> ## Open
> <unresolved high-impact items, or "None">
>
> ## Recommendation
> <next step: proceed to plan? draft spec? schedule another /clarify session?>
> ```
> If "Open" is non-empty, name what would unblock each (e.g., "needs decision from <person>", "needs benchmark data").

Return the summary text to the parent. Parent emits it to the user.

### Phase 4 — Handoff

If invoked by another skill, return control with the clarifications applied. If invoked directly via `/clarify`, ask the user what to do next (proceed, save and stop, schedule follow-up).

## When to skip the subagents

For small artifacts (≤200 lines) or simple requests (≤2 expected questions), run all three phases in the parent. Subagent overhead (boot, spawn, return) outweighs the context savings.

Heuristic: if you can hold the artifact in your head, no subagent.

## Channel fallback templates

The rule (`~/.claude/rules/interaction/clarify-protocol.md`) keeps `AskUserQuestion` as the default channel. When it doesn't fit:

**5+ options, or prose-heavy comparison — markdown table:**

```
**Recommended: <Letter>** — <reasoning>

| Option | Description |
|--------|-------------|
| A | ... |
| B | ... |
| C | ... (up to 5) |
| Short | Provide a different short answer (≤5 words) |

Reply with letter, "yes"/"recommended", or your own short answer.
```

**Pure free-form, no enumerable options — suggested-answer:**

```
**Suggested:** <proposed answer> — <reasoning>

Format: short answer (≤5 words). Reply "yes"/"suggested" to accept, or your own.
```

## 9-category taxonomy (expanded)

1. **Functional scope** — what behavior is in/out
2. **Domain / data model** — entities, relationships, identifiers, ownership
3. **Interaction / UX** — flows, states, error surfaces
4. **Non-functional** — perf, security, availability, latency, cost
5. **Integration** — external systems, contracts, auth boundaries
6. **Edge cases** — empty/null, boundary, concurrent, failure
7. **Constraints** — tech, policy, regulatory, deadline
8. **Terminology** — disambiguate overloaded terms before they cause drift
9. **Completion signals** — "how will we know this is done"

## Worked example

User says: "build a dashboard"

**Phase 1 — inventory** (subagent returns top-5 high-impact questions across the 9-cat taxonomy):

1. (functional scope) primary action — view / drill-down / configure?
2. (data model) data scope — single user / single tenant / multi-tenant?
3. (non-functional) refresh cadence — real-time / minutes / daily?
4. (integration) source — existing API / separate read store / direct DB?
5. (completion signals) v1-done means — specific personas served / specific metrics tracked?

**Phase 2 — parent Q&A loop** (one at a time via `AskUserQuestion`):

```
Q1: What's the primary action?
  Options: A) View metrics (Recommended)  B) Drill into incidents  C) Configure thresholds
User: A
→ clarifications.md updated:
  ## Clarifications
  - Q: primary action → A: view metrics
```

```
Q2: Data scope?
User: multi-tenant

Q3: Refresh cadence?
User: 5-min

Q4: Where does data come from?
User: existing API (read-only)

Q5: Definition of done?
User: 3 personas served, p95 < 500ms
```

**Phase 3 — synthesis** (subagent reads `clarifications.md`, emits):

```
## Resolved
- primary action → view metrics
- data scope → multi-tenant
- refresh → 5-min
- source → existing API (read-only)
- completion → 3 personas, p95 < 500ms

## Open
None

## Recommendation
Proceed to /spec-specify with these constraints. Threat-model the multi-tenant
boundary in plan phase (per `threat-modeling`).
```

## Anti-patterns

- **Batching questions in one turn** — violates the cadence rule. If you catch yourself writing two `?`, stop and split
- **Showing the queued list** — defeats the purpose; the user starts answering ahead and skips context
- **Asking trivia** — if the answer doesn't change a decision, don't ask. The cap of 5 forces this discipline
- **Forgetting atomic update** — if the session is interrupted, the recorded answers must already be in the document; don't batch the writes
- **Calling AskUserQuestion from the inventory subagent** — undocumented whether it bubbles up. Keep all user-facing prompts in the parent

## See also

- `~/.claude/rules/interaction/clarify-protocol.md` — the always-on rule that shapes default behavior
- spec-kit `/speckit.clarify` — upstream inspiration; if a project uses spec-kit, prefer its native command which integrates with the spec template
