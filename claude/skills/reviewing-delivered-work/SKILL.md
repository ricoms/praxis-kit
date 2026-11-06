---
name: reviewing-delivered-work
description: >-
  Review a PR or codebase someone else delivered against the project's
  recorded standard, as a review its author can act on. Use for a teammate's
  PR, or to take stock of code you did not write.
metadata:
  tags:
    - review
    - security
    - github
---

# Reviewing Delivered Work

The deliverable is a review the author can act on. Not a survey, and not a list of everything you
noticed.

## Before any finding

**Find the standard the work was built against, and read it.** A finding that cites a rule nobody
follows burns the author's time and makes the real findings easier to dismiss.

In order: the project's constitution or principles, its ADRs, the spec and plan for this change,
the architecture document, and what the client or product owner recorded. Where our standard and
theirs disagree, theirs wins, and the gap is a question for them, not a review comment.

Two failures to avoid:

- **Citing a standard nobody practises.** Check that a rule is followed somewhere real, including
  in our own reference code, before calling a deviation a violation.
- **Reviewing the diff against itself.** A change can match the code around it and still
  contradict a recorded decision, or look odd locally while doing exactly what the design says.

## Four dimensions, in this order

Earlier ones invalidate later ones.

1. **Does it do what it claims.** Read the description, then reproduce the author's own claims:
   the build, the tests, the scans, the counts. Say what you reproduced and what you did not run.
2. **Security.** The project's articles first, cited by number, then authorisation on every path,
   tenancy scoping, secrets, injection, egress, dependency bounds.
3. **Operational maturity.** Could someone who did not write it run it at 03:00? What alarm
   fires, what the runbook says, whether rollback is a path, whether failure is loud. A green
   check that proves nothing is a defect: say what the gate actually covers.
4. **Tests.** Were expected values fixed before the implementation, from the source of truth
   rather than from the new code? Was any test deleted, skipped or weakened to go green?

When the change moves, renames or replaces docs with pointers, also run the checks in
`authoring-project-docs` § Reviewing a doc change.

## Severity

Only a rule the project marks non-negotiable blocks on its own. Anything else can be accepted by
a named person, so name who would have to accept it.

**Separate what the author can fix from what they cannot.** A finding that needs a client
decision or a team agreement goes to an issue or an ADR, not into a change request.

## Writing it

- **No asks → approve in one line.** Verification notes go to the owner in the session, not into
  the review. A caveat worth keeping is one conversational sentence: "Just make sure the plan
  shows the rules updated in place, ok?"
- **Asks → numbered, first.** One sentence each. `REQUEST_CHANGES` when the review is mostly asks;
  `COMMENT` when the only blocker is not the author's, and say why.
- **Praise only what you verified.**
- Draft it, show it, post it on the owner's word. A posted review that was wrong is edited in
  place, not followed by a correction.
- Once the owner has decided a change to a teammate's PR, commit it to their branch instead of
  writing a suggestion. The commit message is the notice.

## Never findings

AI attribution trailers, and anything else the project has already settled. Style the project
does not record as a rule is a note to the owner, not a finding.

## Anti-patterns

Findings traced to nothing · a standard cited that no one follows · severity inflated to get
attention · praise you did not verify · blocking on a decision the author cannot make · reviewing
without reading what the work was built against · a three-paragraph approval.
