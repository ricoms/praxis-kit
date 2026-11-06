# Data classes — obligations, environments, and the spec block

On-demand detail for `classifying-data`. Open at step 4.

## Obligations per class

| Class | Retention default | Logs | Non-production | Subject rights | At rest |
| --- | --- | --- | --- | --- | --- |
| **Public** | Unbounded | Fine | Fine | — | — |
| **Internal** | Business-defined | Fine | Fine | — | Standard |
| **Personal** | **Bounded, stated in the spec** | Redacted or absent | Synthetic only | Access · deletion · correction · portability | Encrypted |
| **Sensitive personal** | Bounded and short | **Never** | **Never** — synthetic only | As Personal, plus a lawful-basis question | Encrypted, access-logged |
| **Cardholder** | Do not store. If stored, the compliance scope changes | **Never** | **Never** | As Personal | Out of scope for most designs — say so deliberately |
| **Secret** | Rotate on a stated schedule | **Never** | Separate values per environment | — | Secret manager, never source |

**"Never" means the arrangement makes it impossible, not that a filter removes it.** A redaction filter is a runtime condition and runtime conditions fail quietly — a config flag off, an allowlist empty, a new field nobody added to the list. Prefer not collecting the field, not passing it to the sink, or structuring the log so the value has nowhere to go.

## The environment question

For each item, answer per environment rather than once:

| | Production | Staging | Development | Local |
| --- | --- | --- | --- | --- |
| Does this item exist here? | | | | |
| Real or synthetic? | | | | |
| Who can read it? | | | | |

A platform's staging carrying synthetic data bounds *their* environments. Yours are yours to answer.

## Subject rights — the split question

When a record spans two systems, **one side has to serve each right**, and "both" means neither:

- Which side receives the request?
- Which side holds the record — and is it the same side?
- What does the other side have to do, and how is it asked?
- What is the deadline, and who is counting?

Unanswered, this is an issue with an owner, not a paragraph.

## Retention — three honest answers

For every retained item, exactly one of:

1. **Legal obligation** — name it, and the period it sets.
2. **Product requirement** — name the requirement, and what breaks without the data.
3. **Nobody decided.** Say so. This is the common answer and the one that accumulates risk.

Answer 3 with no owner is the finding.

## The spec block

Four lines. Goes in the specification, under the functional requirements.

```markdown
### Data

| Field | Flows | Class | Owner | Retained |
| --- | --- | --- | --- | --- |
| <field> | received · stored · logged | Personal | ours | 90d — product req §N |
| <field> | derived · displayed | Personal | ours | session only |
| <field> | received · transmitted | Internal | platform's | not retained here |

**Survives the session:** <what, and why>
**Never logged:** <fields>
**Non-production:** <synthetic | absent>
**Open:** <undecided item> → issue #<N>, owner <side>
```

Keep it to what this feature touches. A spec that restates the whole system's data model is not read.

## Quick triggers for "this is Personal and you may not think so"

- An IP address, a device identifier, a session identifier tied to a person
- A derived score, flag, category or inference *about* a person
- A free-text field a user can type anything into
- An email address in a URL, a redirect, or an error message
- A correlation identifier, if it can be joined back to a person on either side
- Metadata about a person's activity — timestamps, counts, sequences
- A photograph, a document upload, a signature

## Sources

Class names are deliberately generic so they map onto whichever regime applies. Bind them to a jurisdiction's checklist: LGPD/ANPD, GDPR, CCPA, PCI DSS or SOC 2 — the classification does not change, only the obligations attached to it.
