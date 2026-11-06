---
name: authoring-project-docs
description: >-
  Route each fact to its one doc home (ADR, runbook, README, CHANGELOG,
  OpenAPI), one Diátaxis mode per doc, stating the present. Use when
  creating, moving or reviewing a project doc.
metadata:
  tags:
    - documentation
    - conventions
    - complexity-management
---

# Authoring Project Docs

Routing and refusal, not invention. Every fact has exactly ONE documentation home; everything else links to it. The kit already owns most homes (runbooks, incidents, glossary, OpenAPI, Gherkin, specs, conventional commits) — this skill prevents parallel/duplicate/invented doc surfaces from growing next to them.

## The mode taxonomy (Diátaxis)

Four reader intents; **one mode per document** — mixing modes in one doc is the core failure pattern:

| Mode | Reader intent | Examples here |
|---|---|---|
| tutorial | learning | onboarding walkthrough |
| how-to | doing a task | playbooks, procedures, UPGRADING.md |
| reference | looking up facts | CHANGELOG, OpenAPI, config tables, glossary |
| explanation | understanding why | ADRs, ARCHITECTURE.md |

README is the entry point that *routes* to the four — orientation only, links out, never inlines a tutorial or reference dump.

## The roster (closed — adding a type is a deliberate act, like adding a dep)

| Type | Home | Standard | Update trigger |
|---|---|---|---|
| README.md | repo root | orientation + links; quickstart ≤ 10 lines | entry-path or scope changes |
| ARCHITECTURE.md | repo root | matklad codemap: where things live, boundaries, invariants — NOT rationale | module/boundary changes |
| ADR | `docs/adr/NNNN-<slug>.md` | MADR-lite (below); immutable once accepted; supersede, never edit | each significant decision |
| Playbook | `docs/runbooks/` | symptom-driven: `\|Symptom\|Fix\|` tables, copy-pasteable commands matching the justfile; every alert links its row; the shared template renders the starting set | alert/failure-mode changes |
| Procedure | `docs/runbooks/` | routine manual op, allowed only while automation is pending — `<!-- automate: ... -->` marker; deploy is NEVER a procedure (pipeline-first: CD is the procedure, rollback is a playbook) | new manual op (rare) |
| SLO doc | `docs/slo.md` | per-service SLI spec + objective + measurement window + error-budget policy paragraph; load-testing and alerting gate against it | SLO change or breach review |
| Postmortem | `docs/runbooks/incidents/YYYY-MM-DD-<id>.md` | blameless, any production incident: impact, trigger, detection, timeline, root causes; action items = linked GitHub issues, never checkboxes | each incident |
| CHANGELOG.md | repo root | keepachangelog — **generated** (git-cliff / release-please) from conventional commits; never hand-edited | release (automated) |
| Release notes (user-facing) | project-defined — e.g. `changelog.d/` pending → `docs/changelog/<version>.md` released | plain language for the affected audience — short sentences, one change per sentence, no jargon or invented terms for what shipped; one entry per user-visible change; **generated** from per-change fragments authored in the causing PR — never from commit subjects; a release with no fragments announces nothing | any change to what users see, when they get it, or who receives it |
| UPGRADING.md | repo root | per breaking release: old → new, copy-pasteable | each breaking change |
| OpenAPI | in repo (API9) | contract source of truth; CI-checked against routes | API changes |
| Gherkin features | `tests/`/`features/` | Tier-1 BDD — the living behavior spec | behavior changes |
| Specs | `specs/` + `.specify/` | spec-kit owns lifecycle | per feature |
| Glossary | project docs (setup: `rules/glossary.md`) | cross-cutting terms only; per-domain terms stay in their module/skill | new cross-cutting term |
| Agreements | `docs/agreements.md` | the ten decisions `CONSTITUTION.md` §5 requires: proposed default, status, choice, date, decider | an agreement is settled or changed |
| CONTRIBUTING / SECURITY.md / CODEOWNERS | GitHub-standard locations | GitHub community files | process changes |

## The router — fact → home

- **Decision + rationale** → ADR. Never README, never code comments, never PR-description-only
- **Production symptom → fix** → playbook. Not README, not a wiki
- **Routine manual op** → automate first (justfile/CI); a procedure doc only while automation is pending
- **Reliability target** → SLO doc. Load tests, alerts, and retry tuning reference it — never inline their own targets
- **What changed** → conventional commit → generated CHANGELOG. Hand-writing it is double-entry bookkeeping
- **What changed, for non-technical users** → user-facing release notes, generated from fragments. NOT the developer CHANGELOG — same word, different audience, different source
- **Planned / in-flight work** → GitHub issues + board (`managing-github-issues`). **ROADMAP.md / TODO.md / BACKLOG.md / STATUS.md are forbidden** — markdown state duplicates the board and is stale by default
- **API contract** → OpenAPI. Prose API docs are generated from it, not written beside it
- **Expected behavior** → Gherkin. A prose "functional spec" duplicating scenarios is drift
- **Term definition** → glossary
- **Module layout / invariants** → ARCHITECTURE.md
- **In-code rationale** → only what the kernel comments rule allows: non-obvious runtime behavior + `ceiling:` comments. Everything else → commit/PR/ADR

## Rules (NON-NEGOTIABLE)

1. **One home per fact.** Duplicating content across docs = future contradiction; link instead
2. **Closed roster.** A doc type not in the table requires adding it to the table first — in the project's `CLAUDE.md` or here — with home, standard, and trigger
3. **No doc without an update trigger.** If nothing predictably updates it, it's debt on day one — don't create it
4. **Generated > hand-written** wherever a source of truth exists (CHANGELOG from commits, API docs from OpenAPI, module docs from docstrings)
5. **One Diátaxis mode per doc.** A how-to that drifts into explanation gets split, not extended
6. **Create on first real content.** Never scaffold empty "we'll fill this later" docs — an empty template is over-documentation
7. **Docs state the present — git owns history.** No "Updates"/"History" sections, no dated appendices, no edit trails; delete outdated content, don't annotate it. The ONLY registry-typed docs are append-only *by format*: the ADR *directory* (each file still immutable current-state; reversal = new ADR + `superseded-by`), the generated CHANGELOG, and incident docs / `rotations.log` (audit trails read without git). Never hybridize — a runbook with a dated updates tail is the smell
8. **The repo stands alone for whoever inherits it.** No link into a repo, drive or tracker the inheritor will not have; bring the material across or say inline what the reader needs. A deliverable meant for others lives in the repo, written for them, not as a summary pointing at the real thing elsewhere
9. **Architecture diagrams trace to the infrastructure code.** Each box names the module and resource it comes from; draw only what is built, and update the diagram in the same PR as the resource

## Reviewing a doc change

This section applies to a PR that is mostly prose: docs moved or renamed, text replaced by a pointer, headings changed. `/code-review` looks for defects in code and does not look for these, so run it as well on any code the PR touches. Check in this order:

1. **Every removed claim has a home that says it as strongly.** For each deleted sentence, find where it now lives. A pointer whose target is narrower than the text it replaced loses the difference silently. Put the loss back, or file an issue when restoring it needs a decision
2. **The PR description matches the diff.** Each "moved to" or "replaced by a pointer" in the body names a place where the diff shows it
3. **Old names are gone repo-wide.** Grep every renamed path, heading and anchor. A section other files cite by heading is renamed in the same PR as its citations
4. **Generated files are regenerated** from their source, and the source's own check passes
5. **Edited lines keep the file's wrapping**, and tables and lists still render. Links still resolve, including the relative links inside a moved file, which now start from its new location
6. **Always-on files stay within the budget**, in a repo that has one

Write each finding as the removed text, where it should live, and what a reader can no longer learn.

## ADR — MADR-lite template

```markdown
# NNNN — <decision title>

- Status: proposed | accepted | superseded by [NNNN](NNNN-slug.md)
- Date: YYYY-MM-DD
- Deciders: <the named decider; co-deciders informed>

## Context
<forces, constraints — why a decision was needed>

## Decision
<what was decided, active voice>

## Consequences
<what becomes easier, harder, or locked-in; revisit trigger if any>
```

Sequential numbering, one decision per ADR, accepted ADRs are immutable — a change of mind is a NEW ADR that supersedes.

**Keep it to a screenful:** a few lines of context, each option in a sentence or two with its trade-off, a one-line decision, a handful of consequences. Options that are topologies get a diagram each; options that differ in properties get a table, with only the chosen flow drawn.

**Two ways to accept one:**

- **The merge is the decision.** When the deciders review the PR, write the status as it will be on merge (`accepted`) and let the approvals be the record.
- **Proposed first.** When the text needs arguing before anyone decides: land it `proposed`, open one thin decision issue with the deciders and a date, and accept it in a later PR that the named deciders approve. A decision with no date stays proposed by accident.

An amendment is a new ADR; the old one's index row reads "accepted, amended by NNNN".

## Anti-patterns

ROADMAP.md beside a project board · hand-edited CHANGELOG in a conventional-commits repo · design rationale in README · runbook steps in a PR description · empty scaffolded doc trees · a second glossary · prose duplicating Gherkin · "docs/" dumping ground with no roster mapping · editing an accepted ADR · dated "Update:" appendices in a current-state doc (git already holds that history) · stakeholder announcements generated from commit subjects · a second changelog with no declared audience.

## See also

- `rules/interaction/writing-register.md` — this skill decides *where* a fact lives; that rule decides *how it reads*
- `managing-github-issues` — status/planning home (the ROADMAP.md replacement)
- `template/README.md` in praxis-kit — the runbooks and the justfile recipe contract a new project starts with
- `rules/glossary.md` — the setup's own glossary charter
- Diátaxis (diataxis.fr) · keepachangelog.com · MADR (adr.github.io) · Google SRE book/workbook (playbook-per-alert, SLO docs, blameless postmortems)
