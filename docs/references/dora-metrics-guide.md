---
id: dora.dev/guides/dora-metrics
title: "DORA's software delivery performance metrics"
authors: DORA (DevOps Research and Assessment), a program run by Google Cloud
year: 2026
venue: dora.dev guide, last updated 2026-01-05
url: https://dora.dev/guides/dora-metrics/
license: CC BY 4.0 (Google LLC)
read: the metrics guide and the research index page; not the 2024 or 2025 reports
informs:
  - CONSTITUTION.md#1-what-we-are-after
tags: [velocity, delivery-metrics, stability, throughput, dora]
---

# DORA metrics

**In one sentence:** five delivery metrics, three for throughput and two for instability, which DORA's survey
research finds move together rather than trading off, and which are meant for a team to compare with its own past.

## Claim

Software delivery performance is measured by five metrics:

| Group | Metric | DORA's definition |
|---|---|---|
| Throughput | Change lead time | from commit to version control until deployed in production |
| Throughput | Deployment frequency | deployments over a period, or the time between them |
| Throughput | Failed deployment recovery time | the time to recover from a deployment that fails and needs immediate intervention |
| Instability | Change fail rate | the share of deployments that need immediate intervention afterwards |
| Instability | Deployment rework rate | the share of deployments that are unplanned and happen because of an incident in production |

Speed and stability "are not tradeoffs": the metrics are correlated for most teams, and top performers do well on
all five.

The guide warns against two misuses. Setting the metrics as goals invites gaming them, and comparing very different
applications or teams misleads. The stated aim is for a team to improve on its own past.

## Evidence

- DORA's annual survey of practitioners. The guide summarises findings; it does not
  give sample sizes or methods, and this note did not read the reports that do.

## Adopted

- **Velocity signals** in `CONSTITUTION.md` section 1 use the same names where the meaning matches: change lead
  time, change fail rate, rework rate and recovery time.
- **No targets, no comparison between teams**, stated in section 1, from the guide's warnings. It also serves the
  constitution's goal of calm work.
- **"Velocity, not speed" has support** in the finding that throughput and stability rise together.

## Not adopted

- **Deployment frequency as a signal.** It is reported, but on its own it measures speed, which the constitution
  says not to chase.
- **DORA's exact definitions, in two places.** The constitution's lead time starts when work starts, not at commit,
  because waiting on decisions happens before the first commit. Its rework rate also counts reopened work, not only
  unplanned deployments after an incident.
- **Performance tiers** (elite, high, medium, low). They invite comparison between teams.

## Limits

- Survey-based and correlational: the findings show which practices go together, not which cause what.
- Run by Google Cloud, which sells delivery and platform products.
- Change effort, the constitution's fifth signal, has no DORA counterpart; it comes from the SWE-CI note.
- The 2025 report, described on the index as finding that AI "acts as an amplifier" of a team's existing system,
  was not read. A note on it should come from the report itself.
