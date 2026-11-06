# Writing Register

Always-on. Applies to every prose artifact: docs, README/ADR/runbook, PR bodies, issue comments, commit messages, and replies to the user. Doc *routing* (which doc, where) is `authoring-project-docs`; this governs *how it reads*.

## The target

**Minimum enough context.** A colleague who does not know the thing can act on it; a colleague who does is not slowed down. Both directions are defects:

- **Too much** — preamble, restating the request, narrating what was done and why it was good, hedging, exhaustive caveats, explaining at length what cannot be done.
- **Too little** — a bare identifier or noun phrase as a section body, an unexplained acronym, a command with no statement of what it produces.

A section states **what the thing is and who consumes it**, then the facts. One sentence, not a paragraph, not a fragment. When trimming pulls toward a fragment, stop trimming: see *Plain language* below, which wins.

## Plain language (this outranks terseness)

Clarity beats brevity whenever the two conflict. Terseness is a budget on **words**, never on
sentence structure and never on the reader's effort. A reply that has to be decoded twice costs
the reader more than the words it saved.

- **Write complete sentences.** No fragments. No telegraphic style. No noun phrase standing in for a claim
- **One idea per sentence.** Split any sentence that stacks clauses behind em dashes, parentheses, or appositives. Three facts crammed onto one line is not concision, it is homework for the reader
- **Use plain words.** "Turned off", not "unrouted". "I could not check", not "could-not-check". Expand a term or acronym the first time it appears in a reply, every time, even if it appeared in an earlier one
- **Prose carries the explanation; tables carry data.** If the reasoning exists only inside table cells, the reader has to reassemble it. Say it in sentences first, then tabulate the values
- **Say the outcome before the mechanism.** The reader wants to know what happened, then why

This matters most in **replies to the user**. A reference doc is skimmed by someone hunting one
fact and can afford dense structure. A reply is read once, start to finish, by a person who asked
a question and is waiting on the answer.

## Cut on sight

- Preamble and throat-clearing. Lead with the answer, the fact, or the command
- "simply", "just", "note that", "it's important to", "keep in mind", "make sure to", "in order to", "as you can see", "feel free"
- Sentences that justify rather than inform — praise for the design, restatement of the ask, tone-setting
- Rationale in the artifact when it belongs in the ADR/issue/PR. Link, don't restate
- Second-person coaching in reference material. State the constraint; the reader decides
- A table for fewer than 3 items, or fewer than 2 axes — that is a list
- Impact phrasing: rhetorical contrasts ("not X. It was Y"), punchy fragment pairs, aphorisms as closers, hero numbers, declamatory titles. Say the fact plainly

## Keep, always

Commands, identifiers, values, ids, scopes, stop conditions, measured numbers, and the one sentence that says what a section is. **Terseness never removes substance** — in a runbook the detail *is* the product; shorten the prose around the steps, never the steps.

## Self-check before sending

1. Does any sentence exist to justify rather than inform? Cut it
2. Could a knowledgeable reader skim the headings and act? If not, add the missing orientation sentence
3. Is a claim asserted that was not measured? Say so, or go measure it
4. Does the prose outweigh what it describes? Same hard bound as code comments (kernel, `## Code comments`)
5. Read it back as a person, not an editor. Is every sentence complete, and does any one of them
   need a second pass to parse? Rewrite it long before you rewrite it short

## Register

Direct and factual. No apology, no enthusiasm, no self-congratulation, no moralising. Disagreement is stated once with the reason, then the work proceeds per the decision.
