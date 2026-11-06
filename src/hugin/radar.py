"""Render docs/ai-sdlc/radar.md from radar.toml, or check that it is current and every blip's file exists."""

import sys
import tomllib
from pathlib import Path
from typing import Literal

DATA = Path("docs") / "ai-sdlc" / "radar.toml"
PAGE = Path("docs") / "ai-sdlc" / "radar.md"

RINGS = {
    "adopt": "the template ships it",
    "trial": "a documented alternative, with when to pick it",
    "assess": "a hypothesis: untried, or resting on one engagement",
    "hold": "rejected; do not reintroduce without new evidence",
}
QUADRANTS = {
    "techniques": "Techniques",
    "tools": "Tools",
    "platforms": "Platforms",
    "languages": "Languages and frameworks",
}
FIELDS = {"name", "quadrant", "ring", "why", "ref"}

type Blip = dict[str, str]


def load(root: Path) -> list[Blip]:
    entries = tomllib.loads((root / DATA).read_text()).get("blip")
    if not isinstance(entries, list):
        raise SystemExit(f"{DATA}: `blip` must be an array of tables")
    for n, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or not all(isinstance(v, str) for v in entry.values()):
            raise SystemExit(f"{DATA}: blip {n} must be a table of strings")
    return entries


def problems(blips: list[Blip], root: Path) -> list[str]:
    errors = []
    names: set[str] = set()
    for blip in blips:
        label = blip.get("name", "?")
        if missing := FIELDS - blip.keys():
            errors.append(f"{label}: missing {', '.join(sorted(missing))}")
            continue
        if extra := blip.keys() - FIELDS:
            errors.append(f"{label}: unknown {', '.join(sorted(extra))}")
        if label in names:
            errors.append(f"{label}: listed twice")
        names.add(label)
        if blip["ring"] not in RINGS:
            errors.append(f"{label}: ring {blip['ring']!r} is not one of {', '.join(RINGS)}")
        if blip["quadrant"] not in QUADRANTS:
            errors.append(f"{label}: quadrant {blip['quadrant']!r} is not one of {', '.join(QUADRANTS)}")
        ref = root / blip["ref"]
        if not ref.resolve().is_relative_to(root.resolve()):
            errors.append(f"{label}: {blip['ref']} is outside the kit")
        elif not ref.is_file():
            errors.append(f"{label}: {blip['ref']} does not exist")
    return errors


def render(blips: list[Blip]) -> str:
    lines = [
        "# Technology radar",
        "",
        "Generated from [`radar.toml`](radar.toml) by `hugin radar render`; edit the data, not this page. Each entry",
        "links the file that backs it, and the check fails when that file is gone. Decisions with their",
        "alternatives are in [decision points](decision-points.md).",
        "",
        "| Ring | Meaning |",
        "|---|---|",
        *(f"| {ring.capitalize()} | {meaning} |" for ring, meaning in RINGS.items()),
    ]
    for quadrant, title in QUADRANTS.items():
        lines += ["", f"## {title}", "", "| Ring | Entry | Why | Backed by |", "|---|---|---|---|"]
        for ring in RINGS:
            for blip in blips:
                if blip["quadrant"] == quadrant and blip["ring"] == ring:
                    link = f"[`{blip['ref']}`]({Path('..', '..', blip['ref']).as_posix()})"
                    if blip["ref"].startswith("docs/ai-sdlc/"):
                        link = f"[`{blip['ref']}`]({blip['ref'].removeprefix('docs/ai-sdlc/')})"
                    lines.append(f"| {ring.capitalize()} | {blip['name']} | {blip['why']} | {link} |")
    return "\n".join(lines) + "\n"


def run(command: Literal["render", "check"], root: Path) -> int:
    blips = load(root)
    errors = problems(blips, root)
    page = root / PAGE
    if command == "render" and not errors:
        page.write_text(render(blips))
    elif command == "check" and (not page.exists() or page.read_text() != render(blips)):
        errors.append(f"{PAGE} is stale; run `uv run hugin radar render`")
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0
