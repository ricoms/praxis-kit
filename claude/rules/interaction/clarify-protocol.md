# Clarify Protocol

When asking the user clarifying questions during *any* task. Adapted from spec-kit's `/speckit.clarify`. Full channel templates, worked examples, and the subagent architecture: `clarifying-with-user` skill.

## Cadence (NON-NEGOTIABLE)

1. **One question at a time.** Never reveal queued questions; wait for the answer
2. **Atomic update.** After each answer, immediately update the source of truth and acknowledge
3. **Cap at 5 per session.** More remaining → stop, summarize resolved, ask whether to continue
4. **No batching.** Two `?` in one turn → stop and split

## Channel

Default: `AskUserQuestion` (2–4 options; `(Recommended)` suffix on the first when one is default; `description` carries the tradeoff; 1 question per call). Fallbacks (5+ options → markdown table; pure free-form → suggested-answer format): templates in `clarifying-with-user`.

## Coverage taxonomy (pick highest-impact first, no trivia)

functional scope · domain/data model · interaction/UX · non-functional · integration · edge cases · constraints · terminology · completion signals

## Exemptions

Applies to clarifying questions only — NOT quick pre-destructive-action confirmations, factual lookups, or acknowledgement prompts. Those stay terse and inline.

## Session end

Emit `## Resolved` (Q → A pairs) + `## Open` (unresolved), then proceed with the task.
