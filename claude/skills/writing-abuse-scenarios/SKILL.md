---
name: writing-abuse-scenarios
description: >-
  Name what someone tries that a feature was not built for, at Specify, as
  testable scenarios. Use on any customer-facing or money-moving surface.
metadata:
  tags:
    - security
    - specification
    - abuse-cases
    - spec-kit
---

# Writing Abuse Scenarios

A functional specification says what the feature does when it is used as intended. **Abuse scenarios say what happens when it is not**, and they are the only place some requirements can come from — nobody writes *"the endpoint must survive 100,000 scripted requests"* as a user story, so nothing in a functional spec produces it.

Run at **Specify**, alongside `classifying-data`. Cheap on purpose: no framework, no specialist, one pass per surface. That matters when nobody on the team has run a threat model, which is common and is not a reason to skip this.

**This is not threat modelling.** `threat-modeling` runs at Design against an architecture and walks STRIDE per trust boundary. This runs before a design exists, against a *screen or an endpoint*, and asks one question: what does someone try here?

## When it triggers

- Any customer-facing surface — a form, a lookup, a search, a login, a verification step
- Anything that moves money, issues credit, or cancels a paid thing
- Anything that returns data about a person, keyed on something a stranger could guess
- Any unauthenticated endpoint, and any endpoint authenticated by something weak
- Any surface that costs you money per request

## When it does not

Internal admin tools behind real authentication. Pure presentation changes. Surfaces already covered by a current scenario set — extend it rather than rewriting.

## Process

Copy this checklist into your response and tick off as you progress:

```
Abuse-Scenario Progress:
- [ ] Step 1: List the surfaces — one per screen or endpoint
- [ ] Step 2: Walk the six intents per surface
- [ ] Step 3: Write each as actor + intent + attempt + what they get
- [ ] Step 4: Make each testable, or drop it
- [ ] Step 5: Record in the spec; the ones with no requirement become one
```

### 1. List the surfaces

One row per screen or endpoint a stranger can reach. **Include the ones you think are boring** — a lander that resolves a slug to a library branch is a surface, and a slug is guessable.

### 2. Walk the six intents

Per surface, six questions. Ask them in this order; the first three are where breaches actually come from.

| Intent | The question |
| --- | --- |
| **Enumerate** | Can I learn the set of valid values by trying? Ids, emails, slugs, codes, accounts |
| **Harvest** | If one request returns some data, do many requests return all of it? |
| **Guess** | Is there a secret short enough to brute-force — a code, a PIN, a last-4? |
| **Impersonate** | Can I get someone else's data by asserting I am them, without proving it? |
| **Exhaust** | Can I make this cost you money, or make it unavailable, by repeating it? |
| **Defraud** | Can I get a thing of value twice, or get one I am not entitled to? |

**The combination is the danger, not the single question.** *Enumerate* plus *harvest* is a breach; either alone is usually a nuisance. Name the combination when you see it.

### 3. Write each as actor + intent + attempt + what they get

One line. The shape matters because it forces the scenario to be concrete:

> **A stranger with no account** wants **the list of phone numbers that booked an appointment with a clinic**. They **submit the lookup form with a common 4-digit confirmation code and vary the phone number**, and get **a hit/miss oracle they can script**.

Not *"the endpoint may be vulnerable to enumeration"* — that is a threat, not a scenario, and nobody can test it.

### 4. Make each testable, or drop it

Every scenario becomes a test at Verify — that is what *security test coverage* means. If you cannot state the test, the scenario is too vague to act on.

| Scenario says | Test asserts |
| --- | --- |
| Scripted requests get an oracle | The Nth request within a window is refused |
| A short code can be guessed | The account or session locks after N attempts |
| One request returns another party's data | The response is scoped to the verified party, and a mismatched identifier returns nothing |

A scenario whose test is *"we reviewed it"* is not a scenario.

### 5. Record in the spec; the ones with no requirement become one

Scenarios go in the specification beside the functional requirements. Then the useful part:

**For each scenario, name the requirement that stops it.** Where there is no requirement, **you have just found one** — write it. This is the whole return on the exercise, and it is why the pass belongs at Specify rather than at review.

## Worked example — the requirement nobody wrote

A customer-facing refund portal. Its product requirements listed launch-blocking security controls: verification before data, no anonymous paths, no card-detail lookup, captcha, a blacklist.

It was breached, and the operator's own root causes were three: a lookup that matched on *or* instead of *and*, so a card last-4 enumerated every transaction; no validation that the person was who they claimed; and **no rate limiting, which is what turned a lookup flaw into bulk exfiltration**.

Two of the three were anticipated by the requirements. **Rate limiting was not a product requirement at all** — no user story produces it, so nothing in the functional specification asked for it, and the launch-blocking list that was supposed to be exhaustive did not contain the control that mattered most.

One *Exhaust* row against the lookup surface would have produced it: *a stranger wants every transaction, scripts the form, and gets unlimited attempts.* The requirement writes itself from there.

## Anti-patterns

- **Writing threats instead of scenarios.** *"Vulnerable to enumeration"* names a category; a scenario names an actor doing a thing and getting a result
- **Writing mitigations instead of scenarios.** *"Add rate limiting"* skips the step that justifies it, and skipped justification is what gets cut under deadline
- **Only imagining attackers.** The confused and the desperate produce most of the volume — a customer who submits twice because the page was slow, or who tries every email they own
- **Scenarios with no test.** They read as diligence and change nothing
- **Deferring to the threat model.** Design-stage STRIDE assumes the surfaces and their misuse are already named
- **Stopping at the interesting surfaces.** The lander, the health check and the error page are surfaces

## See also

- `classifying-data` — the other half of the Specify gate: what the data *is*, where this says what people do to it
- `threat-modeling` — Design stage, STRIDE per trust boundary. Consumes these scenarios
- `reviewing-api-security` — OWASP API Top 10; several items are these scenarios generalised
- `bootstrapping-with-spec-kit` — the Specify gate this belongs to
