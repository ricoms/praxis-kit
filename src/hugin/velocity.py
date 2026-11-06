"""Read delivery velocity from a GitHub project board that follows the team kit's fields.

Usage:
  hugin velocity --owner ORG --project N --capacity DAYS [--target MILESTONE] [--input items.json]

Sprints are milestones. An item is done when its Status is Done. Numbers come from the
Estimate, Actual and Remaining Work fields; Phase and `type:` labels group the ratios.
"""

import argparse
import datetime as dt
import json
import statistics
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SMALL_SAMPLE = 5


@dataclass
class Item:
    number: int | None
    sprint: str | None
    due: dt.date | None
    done: bool
    estimate: float | None
    actual: float | None
    remaining: float | None
    phase: str | None
    kind: str | None


def field_key(name: str) -> str:
    return name[:1].lower() + name[1:]


def number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def load(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.input:
        raw = json.loads(Path(args.input).read_text())
    else:
        out = subprocess.run(
            ["gh", "project", "item-list", str(args.project), "--owner", args.owner,
             "--limit", "5000", "--format", "json"],
            check=True, capture_output=True, text=True,
        ).stdout
        raw = json.loads(out)
    items: list[dict[str, Any]] = raw["items"]
    return items


def parse(raw: list[dict[str, Any]], args: argparse.Namespace) -> list[Item]:
    items = []
    for r in raw:
        if (r.get("content") or {}).get("type") != "Issue":
            continue
        milestone = r.get("milestone") or {}
        due = milestone.get("dueOn")
        labels = r.get("labels") or []
        kinds = [label.removeprefix("type:") for label in labels if label.startswith("type:")]
        kinds += [label for label in labels if label in ("question", "bug", "enhancement")]
        items.append(Item(
            number=(r.get("content") or {}).get("number"),
            sprint=milestone.get("title"),
            due=dt.date.fromisoformat(due[:10]) if due else None,
            done=r.get("status") == args.done_status,
            estimate=number(r.get(field_key(args.estimate_field))),
            actual=number(r.get(field_key(args.actual_field))),
            remaining=number(r.get(field_key(args.remaining_field))),
            phase=r.get(field_key(args.phase_field)) or None,
            kind=kinds[0] if kinds else None,
        ))
    return items


def sprints(items: list[Item]) -> list[dict[str, Any]]:
    by_sprint: dict[str, list[Item]] = defaultdict(list)
    dues: dict[str, dt.date | None] = {}
    for it in items:
        if it.sprint:
            by_sprint[it.sprint].append(it)
            dues[it.sprint] = it.due
    order = sorted(by_sprint, key=lambda s: (dues[s] or dt.date.max, s))
    return [{"sprint": s, "due": dues[s],
             "planned": sum(it.estimate or 0 for it in by_sprint[s]),
             "done": sum(it.estimate or 0 for it in by_sprint[s] if it.done),
             "open": sum(1 for it in by_sprint[s] if not it.done)} for s in order]


def margin(items: list[Item], capacity: float, target: str, today: dt.date) -> dict[str, Any]:
    dues = {it.sprint: it.due for it in items if it.sprint and it.due}
    match = [s for s in dues if target.lower() in s.lower()]
    if len(match) != 1:
        return {"target": target, "matches": len(match)}
    target_due = dues[match[0]]
    in_scope = {s for s, d in dues.items() if d <= target_due}
    sprints_left = sum(1 for s in in_scope if dues[s] >= today)
    work_left = sum((it.remaining if it.remaining is not None else it.estimate or 0)
                    for it in items if it.sprint in in_scope and not it.done)
    room = capacity * sprints_left
    return {"target": match[0], "due": target_due, "sprints_left": sprints_left, "capacity_left": room,
            "work_left": work_left, "margin": room - work_left}


def ratios(items: list[Item], group: str) -> dict[str, dict[str, float]]:
    pairs: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for it in items:
        key = it.phase if group == "phase" else it.kind
        if it.done and key and it.estimate and it.actual is not None:
            pairs[key].append((it.estimate, it.actual))
    return {key: {"pairs": len(p), "ratio": sum(a for _, a in p) / sum(e for e, _ in p),
                  "median": statistics.median(a / e for e, a in p), "small_sample": len(p) < SMALL_SAMPLE}
            for key, p in sorted(pairs.items())}


def coverage(items: list[Item]) -> dict[str, int]:
    estimated = [it for it in items if it.done and it.estimate]
    missing = sum(1 for it in estimated if it.actual is None)
    return {"estimated_done": len(estimated), "with_actual": len(estimated) - missing, "missing": missing}


def sprint_table(items: list[Item], capacity: float) -> list[str]:
    lines = ["| Sprint | Due | Planned (d) | Done (d) | Done ÷ capacity | Open items |", "|---|---|--:|--:|--:|--:|"]
    for r in sprints(items):
        lines.append(f"| {r['sprint']} | {r['due'] or '—'} | {r['planned']:.1f} | {r['done']:.1f} "
                     f"| {r['done'] / capacity:.0%} | {r['open']} |")
    return lines


def margin_line(m: dict[str, Any], capacity: float) -> str:
    if "margin" not in m:
        return f"Target milestone matching {m['target']!r}: {m['matches']} found; pass a unique part of its title."
    return (f"Margin to **{m['target']}** (due {m['due']}): {m['sprints_left']} sprints × {capacity:g} d = "
            f"{m['capacity_left']:.1f} d of capacity, {m['work_left']:.1f} d of open work → **{m['margin']:+.1f} d**.")


def ratio_table(items: list[Item], group: str) -> list[str]:
    rows = ratios(items, group)
    if not rows:
        return [f"No estimate/actual pairs by {group}."]
    lines = [f"| {group.title()} | Pairs | ΣA ÷ ΣE | Median A ÷ E |", "|---|--:|--:|--:|"]
    for key, r in rows.items():
        flag = " (small sample)" if r["small_sample"] else ""
        lines.append(f"| {key}{flag} | {r['pairs']} | {r['ratio']:.2f} | {r['median']:.2f} |")
    return lines


def coverage_line(c: dict[str, int], actual_field: str) -> str:
    return (f"{c['with_actual']} of {c['estimated_done']} done estimated issues have an {actual_field}; "
            f"{c['missing']} missing.")


def positive_days(value: str) -> float:
    days = float(value)
    if days <= 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive number of engineer-days")
    return days


def add_board_args(p: argparse.ArgumentParser, *, capacity_required: bool = False) -> list[str]:
    actions = [
        p.add_argument("--capacity", type=positive_days, required=capacity_required, help="engineer-days per sprint"),
        p.add_argument("--target", help="part of the milestone title to measure the margin to"),
        p.add_argument("--done-status", default="Done"),
        p.add_argument("--estimate-field", default="Estimate"),
        p.add_argument("--actual-field", default="Actual"),
        p.add_argument("--remaining-field", default="Remaining Work"),
        p.add_argument("--phase-field", default="Phase"),
    ]
    return [a.dest for a in actions]


def add_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--owner", required=True)
    p.add_argument("--project", required=True, type=int)
    p.add_argument("--input", help="read items from a saved `gh project item-list --format json` file")
    p.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    add_board_args(p, capacity_required=True)


def run(args: argparse.Namespace) -> int:
    items = parse(load(args), args)
    out = ["## Velocity", "", *sprint_table(items, args.capacity), ""]
    if args.target:
        out += [margin_line(margin(items, args.capacity, args.target, args.today), args.capacity), ""]
    out += ["### Actual ÷ estimate by phase", "", *ratio_table(items, "phase"), ""]
    out += ["### Actual ÷ estimate by type", "", *ratio_table(items, "type"), ""]
    out += [coverage_line(coverage(items), args.actual_field)]
    print("\n".join(out))
    return 0

