---
name: classifying-data
description: >-
  Classify a feature's data at spec time: its class, flows, and the retention,
  logging and environment duties that follow. Use at Specify on any feature
  handling personal, financial or credential data.
metadata:
  tags:
    - security
    - privacy
    - specification
    - data-classification
    - spec-kit
---

# Classifying Data

Run this **at Specify, before a design exists.** It is the cheapest point at which retention, redaction and deletion obligations are still design inputs rather than retrofits — and the point at which spec-driven tooling asks nothing about data at all.

The output is four lines in the spec, not a document: what the feature touches, its class, what survives the session, and which obligations follow. It feeds `threat-modeling` at Design, which then asks who can *attack* what this names.

Per-class obligations, the environment matrix, and the spec block template: [data-classes.md](data-classes.md).

## When it triggers

- Any feature receiving, deriving, storing, logging or displaying data about a person
- Any feature touching payment, account or transaction data
- Any new field on an existing screen or endpoint — **a field is the unit, not a feature**
- Any new log line, telemetry event or analytics payload
- Any change to what survives a session, or for how long

## When it does not

Pure refactors with no new field and no new sink. Static content. Internal tooling over data already classified.

## Process

Copy this checklist into your response and tick off as you progress:

```
Data-Classification Progress:
- [ ] Step 1: Inventory the fields, by flow
- [ ] Step 2: Classify each — and classify the flow, not the field alone
- [ ] Step 3: Mark what survives the session
- [ ] Step 4: Derive obligations, and name who owns each
- [ ] Step 5: Record in the spec; hand the unresolved items to an owner
```

### 1. Inventory the fields, by flow

List every field, and for each, **which flows it takes**. The flow is what decides the obligation:

| Flow | Ask |
| --- | --- |
| **Received** | From the user, or from an upstream system? |
| **Derived** | Computed *about* a person — a score, a flag, an inference |
| **Stored** | Which store, and in what column |
| **Logged** | Application logs, access logs, traces, error reports |
| **Displayed** | On screen, and in a URL |
| **Transmitted** | To which third party, under what agreement |
| **Retained** | What is still there after the session ends |

**Derived data is the one that gets missed.** A fraud score, a "likely duplicate" flag, an inferred category — computed about a person, so it is personal data, and it usually has no owner because nobody typed it in.

### 2. Classify each — and classify the flow, not the field alone

| Class | What it is |
| --- | --- |
| **Public** | No restriction |
| **Internal** | Business data, no subject rights |
| **Personal** | Identifies or relates to a person. Subject rights apply |
| **Sensitive personal** | Special category — health, biometric, government ID, financial account |
| **Cardholder** | Payment card data. Triggers a compliance scope, so its presence is a design decision, not a detail |
| **Secret** | Credentials, tokens, keys. Never logged, never persisted in clear |

**The same field changes class with its flow.** An email address is Personal in a column, and is a defect in a log line or a URL. Classify `field × flow`, not `field`.

### 3. Mark what survives the session

For each stored or retained item: **why does it still exist after the request?** Three honest answers — a legal obligation, a product requirement, or nobody decided. The third is the common one and it is where retention risk accumulates.

An item nobody can justify keeping is the cheapest thing to remove, and removal is the only mitigation that cannot fail at runtime.

### 4. Derive obligations, and name who owns each

Per class, from [data-classes.md](data-classes.md): retention default, log rule, environment rule, subject-rights applicability, encryption. For each obligation, **name the side that owns it.**

**The trap worth naming explicitly:** when a vendor or platform says production data is *out of your scope*, that bounds what you can reach of **theirs**. It says nothing about what your own system holds. Read the exclusion as a boundary on their data, never as a claim about yours.

### 5. Record in the spec; hand the unresolved items to an owner

Four lines in the spec — template in [data-classes.md](data-classes.md). Anything undecided (a retention period, which side serves a deletion request) becomes an issue with an owner, not a sentence in a document.

## Worked example — the failure this prevents

A class-booking tool built by a vendor against a gym chain's member API. The gym chain's scoping document said production database access, gateway credentials and production member records were all outside the vendor's scope.

The security artifact read that and concluded *"no environment we touch holds real member data"* — then narrowed its retention and data-handling section on that basis.

**The exclusion was about the gym chain's data.** Identification in the booking tool was phone-number-only, so the vendor's own production database held verified phone numbers, booking state, and a record of what each session displayed — real personal data, in an environment they owned and operated. Retention, redaction and deletion-request obligations all applied and the artifact had just argued they were narrow.

Nobody classified. One inventory pass at Specify would have caught it, because the first row would have been *phone number · received, stored, retained · Personal · ours*.

## Anti-patterns

- **Classifying tables instead of flows.** The column is usually fine; the log line is the leak
- **Treating a vendor's scope exclusion as a statement about your own system**
- **Deferring classification to the threat model.** Design-stage STRIDE asks who can attack the data; it assumes someone already said what the data *is*
- **Producing a document.** The output belongs in the spec, where the implementer reads it
- **Leaving retention as "TBD" in prose.** Undecided is fine; undecided with no owner is not
- **Omitting derived data.** Nobody typed it, so nobody classifies it

## See also

- [data-classes.md](data-classes.md) — per-class obligations, environment matrix, spec block template
- `threat-modeling` — Design stage; consumes this and asks who can attack it
- `isolating-multi-tenant-llm` — when the class is per-tenant rather than per-person
- `bootstrapping-with-spec-kit` — the Specify gate this belongs to
