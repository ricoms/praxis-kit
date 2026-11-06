"""Profile resolver + symlink installer for praxis-kit, run as `hugin profiles`.

Commands (add `--kit DIR` before the command to act on another kit with the same profiles/ + claude/ layout,
such as a personal kit installed on top of this one; only this repo installs CLAUDE.md and CONSTITUTION.md, and a
kit's profiles cannot extend this repo's profiles; an item whose name another kit already links is reported TAKEN
and left alone):
  list                                List profiles + descriptions
  install [PROFILE...]                Symlink profiles into ~/.claude/ (default: all)
  install-project DIR PROFILE...      Symlink profiles into DIR/.claude/
  validate                            Check every artifact belongs to >=1 profile, every agent's tool grant
                                       covers what its skill invokes (+ description lint warnings)
  budget [LIMIT]                      Sum always-on bytes (CLAUDE.md + rules + skill descriptions); fail over LIMIT
                                       (LIMIT is required with --kit: BUDGET_LIMIT ratchets this repo only)
  budget PROFILE                      Scope the same breakdown to one profile's resolved set (informational, no ratchet)
  doctor [TARGET]                     Two-way drift check: repo vs TARGET/.claude (default ~)
  resolve PROFILE                     Print merged set as JSON (for debugging)

Profile JSON shape:
  {
    "description": "...",
    "extends": "<parent>",     # optional, single-level
    "skills":   [...],         # dir names under claude/skills/
    "agents":   [...],         # file names under claude/agents/
    "commands": [...],         # file names under claude/commands/
    "rules":    [...],         # file/dir names under claude/rules/
    "assets":   [...]          # paths under claude/ (e.g., "spec-kit")
  }
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from hugin import kit

REPO: Path
PROFILES_DIR: Path
CLAUDE_SRC: Path


def configure(shared: Path, overlay: Path | None = None) -> None:
    global REPO, PROFILES_DIR, CLAUDE_SRC
    root = overlay or shared
    REPO, PROFILES_DIR, CLAUDE_SRC = shared, root / "profiles", root / "claude"


def is_shared_root() -> bool:
    return CLAUDE_SRC == REPO / "claude"


KINDS = ("skills", "agents", "commands", "rules", "assets")


def load_profile(name: str) -> dict[str, Any]:
    p = PROFILES_DIR / f"{name}.json"
    if not p.exists():
        raise FileNotFoundError(f"Profile not found: {name}")
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as error:
        raise ValueError(f"{p}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"{p}: a profile must be a JSON object")
    return data


def resolve(name: str, _seen: set[str] | None = None) -> dict[str, list[str]]:
    """Resolve a profile + extends chain into a flat merged set."""
    _seen = _seen or set()
    if name in _seen:
        raise ValueError(f"Circular profile dependency: {name}")
    _seen = _seen | {name}
    profile = load_profile(name)
    merged: dict[str, list[str]] = {k: [] for k in KINDS}
    if profile.get("extends"):
        parent = resolve(profile["extends"], _seen)
        for k in KINDS:
            merged[k] = list(parent[k])
    for k in KINDS:
        for item in profile.get(k, []):
            if item not in merged[k]:
                merged[k].append(item)
    return merged


def link_item(src: Path, tgt: Path, label: str) -> None:
    tgt.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        print(f"  MISS {label} (source missing)")
        return
    if tgt.is_symlink():
        if tgt.readlink() == src:
            print(f"  OK   {label}")
            return
        if tgt.exists():
            print(f"  TAKEN {label} → {tgt.readlink()} (another kit owns this name; remove that link to switch)")
            return
        tgt.unlink()
    if tgt.exists():
        print(f"  SKIP {label} (local file/dir, not a symlink)")
        return
    os.symlink(src, tgt)
    print(f"  LINK {label}")


def install(profiles: list[str], target_root: Path) -> None:
    base = target_root / ".claude"
    print(f"=== Installing {profiles} into {base} ===")
    base.mkdir(parents=True, exist_ok=True)

    if is_shared_root():
        link_item(CLAUDE_SRC / "CLAUDE.md", base / "CLAUDE.md", "CLAUDE.md")
        link_item(REPO / "CONSTITUTION.md", base / "CONSTITUTION.md", "CONSTITUTION.md")

    merged: dict[str, list[str]] = {k: [] for k in KINDS}
    for name in profiles:
        r = resolve(name)
        for k in KINDS:
            for item in r[k]:
                if item not in merged[k]:
                    merged[k].append(item)

    for kind in KINDS:
        items = merged[kind]
        if not items:
            continue
        print(f"-- {kind} --")
        for item in items:
            if kind == "assets":
                src = CLAUDE_SRC / item
                tgt = base / item
                label = f"{kind}/{item}"
            elif kind == "agents":
                # Convention: bare names in JSON; .md appended at link time
                fname = item if item.endswith(".md") else f"{item}.md"
                src = CLAUDE_SRC / kind / fname
                tgt = base / kind / fname
                label = f"{kind}/{fname}"
            else:
                src = CLAUDE_SRC / kind / item
                tgt = base / kind / item
                label = f"{kind}/{item}"
            link_item(src, tgt, label)

    if target_root != Path.home():
        print("-- cost of this install --")
        n = _kernel_size()
        print(f"  {n:>7}  CLAUDE.md")
        total = n + _scoped_budget(merged["rules"], merged["skills"], "this install")
        print(f"  {total:>7}  TOTAL (~{total // 4} tokens)")


def cmd_list() -> None:
    for p in sorted(PROFILES_DIR.glob("*.json")):
        if p.name == "projects.schema.json":
            continue
        data = load_profile(p.stem)
        ext = f"  [extends: {data['extends']}]" if "extends" in data else ""
        print(f"{p.stem:<22}{ext}")
        print(f"  {data.get('description', '')}")


def _frontmatter(md: Path) -> str:
    import re

    m = re.search(r"^---\n(.*?)\n---", md.read_text(), re.S)
    return m.group(1) if m else ""


def _agent_tools(agent_md: Path) -> set[str] | None:
    """None when the agent has no tools: line, so it inherits every tool."""
    import re

    tm = re.search(r"^tools:[ \t]*(?:\[([^\]]*)\][ \t]*|(.*(?:\n[ \t]+-.*)*))$", _frontmatter(agent_md), re.M)
    if not tm:
        return None
    listed = tm.group(1) if tm.group(1) is not None else tm.group(2)
    return {t.strip().lstrip("-").strip().strip("\"'") for t in re.split(r"[,\n]", listed)} - {""}


def _target_skill_dir(agent_md: Path) -> Path | None:
    import re

    m = re.search(r"~/\.claude/skills/([a-zA-Z0-9_-]+)/SKILL\.md", agent_md.read_text())
    if not m:
        return None
    own = CLAUDE_SRC / "skills" / m.group(1)
    return own if own.exists() else REPO / "claude" / "skills" / m.group(1)


def _skill_needed_tools(skill_md: Path) -> set[str]:
    """Tool names in a skill's allowed-tools and metadata.requires-tools; Bash(git *) counts as Bash."""
    import re

    front = _frontmatter(skill_md)
    meta = re.search(r"^metadata:[ \t]*\n((?:[ \t]+.*(?:\n|$))*)", front, re.M)
    fields = [re.search(r"^allowed-tools:(?P<value>.*(?:\n[ \t]+.*)*)", front, re.M)]
    if meta:
        fields.append(re.search(r"^([ \t]+)requires-tools:(?P<value>.*(?:\n\1[ \t]+.*)*)", meta.group(1), re.M))
    tools: set[str] = set()
    for fm in filter(None, fields):
        value = re.sub(r"(^|\s)#.*", "", fm.group("value"), flags=re.M)
        tools |= set(re.findall(r"\b([A-Z][A-Za-z]*)(?:\([^)]*\))?", value))
    return tools


# Tool -> an unambiguous, mechanically-reliable marker that the skill actually
# invokes it. Prose skill-name mentions ("the `foo` skill", "invoke `/foo`")
# are deliberately excluded: they false-positive, because a doc pointer isn't a
# Skill-tool call.
_TOOL_MARKERS = {
    "AskUserQuestion": r"\bAskUserQuestion\b",
    "Agent": r"\bAgent\(",
    "Skill": r"\bSkill\(",
    "TaskCreate": r"\bTaskCreate\(",
}


def check_agent_tool_grants() -> int:
    """Every agent's tools: grant must cover what its target skill invokes."""
    import re

    errors = 0
    agents_dir = CLAUDE_SRC / "agents"
    if not agents_dir.exists():
        return 0
    for agent_md in sorted(agents_dir.glob("*.md")):
        skill_dir = _target_skill_dir(agent_md)
        if skill_dir is None or not skill_dir.exists():
            continue
        granted = _agent_tools(agent_md)
        if granted is None:
            continue
        if re.search(r"^requires-tools:", _frontmatter(skill_dir / "SKILL.md"), re.M):
            print(f"MISPLACED requires-tools: {skill_dir.name} declares it top-level; move it under metadata:")
            errors += 1
        skill_text = "\n".join(p.read_text() for p in skill_dir.rglob("*.md"))
        for tool in sorted(_skill_needed_tools(skill_dir / "SKILL.md") - granted):
            print(
                f"TOOL GRANT GAP: {agent_md.name} follows {skill_dir.name}, "
                f"whose allowed-tools or metadata.requires-tools declares {tool}, but tools: doesn't include it"
            )
            errors += 1
        for tool, marker in _TOOL_MARKERS.items():
            if re.search(marker, skill_text) and tool not in granted:
                print(
                    f"TOOL GRANT GAP: {agent_md.name} follows {skill_dir.name}, "
                    f"which invokes {tool}, but tools: doesn't include it"
                )
                errors += 1
    return errors


def _first_cells(text: str, header: str) -> list[str]:
    start = text.find(header)
    if start < 0:
        return []
    cells = []
    for line in text[start:].splitlines()[2:]:
        if not line.startswith("|"):
            break
        cells.append(line.split("|")[1].strip())
    return cells


def check_spec_kit_gates() -> int:
    """Every practice in CONSTITUTION.md section 4 needs a gate row in the spec-kit skeleton, and nothing else."""
    practices = _first_cells((REPO / "CONSTITUTION.md").read_text(), "| Practice | explore")
    gates = _first_cells((CLAUDE_SRC / "spec-kit" / "constitution.md").read_text(), "| Practice | Spec-kit gate")
    if not practices or not gates:
        print("SPEC-KIT: cannot find the practice table in CONSTITUTION.md or the gate table in the skeleton")
        return 1
    missing, extra = set(practices) - set(gates), set(gates) - set(practices)
    dupes = sorted({g for g in gates if gates.count(g) > 1})
    for d in dupes:
        print(f"SPEC-KIT: more than one gate for practice: {d}")
    text = (CLAUDE_SRC / "spec-kit" / "constitution.md").read_text()
    empty = [p for p in practices if f"| {p} |  |" in text or f"| {p} | |" in text]
    for e in empty:
        print(f"SPEC-KIT: empty gate for practice: {e}")
    for p in sorted(missing):
        print(f"SPEC-KIT: no gate for practice: {p}")
    for g in sorted(extra):
        print(f"SPEC-KIT: gate for a practice CONSTITUTION.md does not list: {g}")
    return len(missing) + len(extra) + len(dupes) + len(empty)


def cmd_validate() -> int:
    in_profiles: dict[str, set[str]] = {k: set() for k in KINDS}
    for p in PROFILES_DIR.glob("*.json"):
        if p.name == "projects.schema.json":
            continue
        data = load_profile(p.stem)
        for k in KINDS:
            in_profiles[k].update(data.get(k, []))

    errors = 0
    for kind in ("skills", "agents", "commands", "rules"):
        src = CLAUDE_SRC / kind
        if not src.exists():
            continue
        if kind == "skills":
            actual = {d.name for d in src.iterdir() if d.is_dir()}
        elif kind == "agents":
            # Convention: bare names in JSON, .md on disk — strip suffix when comparing
            actual = {f.stem for f in src.iterdir() if f.is_file() and f.suffix == ".md"}
        elif kind == "commands":
            actual = {f.name for f in src.iterdir() if f.is_file() and f.suffix == ".md"}
        else:  # rules — mix of files and dirs
            actual = {p.name for p in src.iterdir()}
        orphans = actual - in_profiles[kind]
        if orphans:
            print(f"ORPHAN {kind}:")
            for o in sorted(orphans):
                print(f"  - {o}")
            errors += len(orphans)
    errors += check_agent_tool_grants()
    if is_shared_root():
        errors += check_spec_kit_gates()
    if errors == 0:
        print("OK — every artifact belongs to >=1 profile, and every agent's tool grant covers what its skill invokes")
    return errors


def cmd_resolve(name: str) -> None:
    print(json.dumps(resolve(name), indent=2))


# ── Token-budget + drift tooling ──────────────────────────────────

DESC_MAX = 350          # chars; descriptions load into EVERY session's prompt
# Ratchet: fails on growth above the current footprint; lower it as trims land (aspiration ~24KB).
BUDGET_LIMIT = 24_915   # bytes of always-on context (CLAUDE.md + rules + descriptions)


def _frontmatter_description(skill_md: Path) -> str:
    import re
    dm = re.search(r"^description:\s*(.*?)(?=^[a-zA-Z_-]+:|\Z)", _frontmatter(skill_md), re.S | re.M)
    if not dm:
        return ""
    raw = re.sub(r"^[>|][+-]?", "", dm.group(1).strip())
    return " ".join(raw.split())


def _scoped_budget(rule_names: list[str], skill_names: list[str], label: str) -> int:
    """Print + return the byte cost of a specific rules/skills selection (e.g. one profile)."""
    rule_paths = [CLAUDE_SRC / "rules" / name for name in rule_names]
    rn = sum(
        p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        for p in rule_paths if p.exists()
    )
    print(f"  {rn:>7}  rules/ ({len(rule_names)} entries — {label})")
    descs = sum(
        len(_frontmatter_description(CLAUDE_SRC / "skills" / name / "SKILL.md"))
        for name in skill_names
        if (CLAUDE_SRC / "skills" / name / "SKILL.md").exists()
    )
    print(f"  {descs:>7}  skill descriptions ({len(skill_names)} skills — {label})")
    return rn + descs


def _kernel_size() -> int:
    return (CLAUDE_SRC / "CLAUDE.md").stat().st_size if is_shared_root() else 0


def cmd_budget(limit: int = BUDGET_LIMIT, profile: str | None = None) -> int:
    """Sum the bytes every session pays before the conversation starts.

    With `profile`, scope to that profile's resolved rules+skills instead of
    the whole repo — the cost of one curated install, informational only
    (no ratchet: a profile is a deliberate choice, not the always-on tax)."""
    n = _kernel_size()
    print(f"  {n:>7}  CLAUDE.md")

    if profile:
        resolved = resolve(profile)
        total = n + _scoped_budget(resolved["rules"], resolved["skills"], f"profile {profile!r}")
        print(f"  {total:>7}  TOTAL (~{total // 4} tokens)")
        return 0

    total = n
    rules = sorted((CLAUDE_SRC / "rules").rglob("*.md")) if (CLAUDE_SRC / "rules").exists() else []
    rn = sum(p.stat().st_size for p in rules)
    print(f"  {rn:>7}  rules/ ({len(rules)} files — ALL auto-load, always-on)")
    total += rn
    descs = sum(
        len(_frontmatter_description(d / "SKILL.md"))
        for d in sorted((CLAUDE_SRC / "skills").iterdir() if (CLAUDE_SRC / "skills").exists() else [])
        if (d / "SKILL.md").exists()
    )
    print(f"  {descs:>7}  skill descriptions (frontmatter, always-on)")
    total += descs
    print(f"  {total:>7}  TOTAL (~{total // 4} tokens)   [limit {limit}]")
    if total > limit:
        print(f"OVER BUDGET by {total - limit} bytes")
        return 1
    print("Within budget")
    return 0


def cmd_doctor(target_root: Path) -> int:
    """Two-way drift check: repo artifacts vs the installed .claude tree."""
    base = target_root / ".claude"
    problems = 0
    kernel = base / "CLAUDE.md"
    shared = (("CLAUDE.md", CLAUDE_SRC / "CLAUDE.md"), ("CONSTITUTION.md", REPO / "CONSTITUTION.md"))
    for name, src in shared if is_shared_root() else ():
        path = base / name
        if path.is_symlink():
            if not path.exists():
                print(f"  DANGLING  {name} → {path.readlink()} (re-run the install)")
                problems += 1
            elif path.readlink() != src:
                print(f"  FOREIGN   {name} → {path.readlink()}  (another setup; fine)")
        elif path.exists():
            print(f"  COPY      {name} — not a symlink; installer cannot update it")
            problems += 1
        elif name == "CONSTITUTION.md" and kernel.is_symlink() and kernel.readlink() == CLAUDE_SRC / "CLAUDE.md":
            print(f"  MISSING   {name} — the kernel points at it; re-run the install")
            problems += 1
    for kind in ("skills", "agents", "commands", "rules"):
        src_dir = CLAUDE_SRC / kind
        tgt_dir = base / kind
        if not tgt_dir.exists():
            continue
        repo_names = {p.name for p in src_dir.iterdir()} if src_dir.exists() else set()
        for item in sorted(tgt_dir.iterdir()):
            if item.is_symlink():
                dest = item.readlink()
                if str(dest).startswith(str(CLAUDE_SRC)):
                    if not dest.exists():
                        hint = "just clean-stale" if is_shared_root() else f"just clean-stale {CLAUDE_SRC.parent}"
                        print(f"  DANGLING  {kind}/{item.name} → removed repo artifact (run `{hint}`)")
                        problems += 1
                else:
                    print(f"  FOREIGN   {kind}/{item.name} → {dest}  (another setup; fine)")
            elif item.name in repo_names:
                print(f"  COPY      {kind}/{item.name} — repo artifact as real dir; installer SKIPs it (convert to symlink)")
                problems += 1
            else:
                print(f"  UNTRACKED {kind}/{item.name} — only in {base}, not under version control")
                problems += 1
    print("OK — installed tree matches repo" if problems == 0 else f"{problems} drift problem(s)")
    return problems


def lint_descriptions() -> None:
    """Warn (not fail) on bloated or trigger-less skill descriptions."""
    import re
    for d in sorted((CLAUDE_SRC / "skills").iterdir() if (CLAUDE_SRC / "skills").exists() else []):
        md = d / "SKILL.md"
        if not md.exists():
            continue
        desc = _frontmatter_description(md)
        warns = []
        if len(desc) > DESC_MAX:
            warns.append(f"{len(desc)} chars (max {DESC_MAX})")
        if not re.search(r"\buse\b", desc, re.I):
            warns.append('no "Use when …" trigger')
        if warns:
            print(f"WARN description {d.name}: {'; '.join(warns)}")


def kit_dir(value: str) -> Path:
    path = Path(value).resolve()
    if not (path / "profiles").is_dir():
        raise argparse.ArgumentTypeError(f"{value} has no profiles/ directory")
    return path


def add_arguments(p: argparse.ArgumentParser) -> None:
    kit.add_root_argument(p)
    p.add_argument("--kit", type=kit_dir, help="act on another kit with the same profiles/ + claude/ layout, such as a personal kit")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("list", help="list profiles and their descriptions")
    install_cmd = sub.add_parser("install", help="symlink profiles into ~/.claude/ (default: all)")
    install_cmd.add_argument("profiles", nargs="*")
    project_cmd = sub.add_parser("install-project", help="symlink profiles into DIR/.claude/")
    project_cmd.add_argument("dir", type=Path)
    project_cmd.add_argument("profiles", nargs="+")
    sub.add_parser("validate", help="check every artifact belongs to a profile and every agent's tool grant")
    budget_cmd = sub.add_parser("budget", help="sum the always-on bytes against LIMIT, or break down one PROFILE")
    budget_cmd.add_argument("limit_or_profile", nargs="?", metavar="LIMIT|PROFILE")
    doctor_cmd = sub.add_parser("doctor", help="two-way drift check: repo vs TARGET/.claude (default ~)")
    doctor_cmd.add_argument("target", nargs="?", type=Path)
    resolve_cmd = sub.add_parser("resolve", help="print a profile's merged set as JSON")
    resolve_cmd.add_argument("profile")


def run(args: argparse.Namespace) -> int:
    configure(kit.root(args.root), args.kit)
    try:
        return _dispatch(args)
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"hugin profiles: {error}") from None


def _dispatch(args: argparse.Namespace) -> int:
    if args.action == "list":
        cmd_list()
        return 0
    if args.action == "install":
        profiles = args.profiles or [
            p.stem for p in sorted(PROFILES_DIR.glob("*.json"))
            if p.stem != "projects.schema"
        ]
        install(profiles, Path.home())
        return 0
    if args.action == "install-project":
        install(args.profiles, args.dir.resolve())
        return 0
    if args.action == "validate":
        errors = cmd_validate()
        lint_descriptions()
        return 1 if errors else 0
    if args.action == "budget":
        value = args.limit_or_profile
        if value and not value.isdigit():
            return cmd_budget(profile=value)
        if not value and not is_shared_root():
            print("budget --kit needs an explicit LIMIT: BUDGET_LIMIT ratchets praxis-kit only")
            return 2
        return cmd_budget(int(value) if value else BUDGET_LIMIT)
    if args.action == "doctor":
        return 1 if cmd_doctor(args.target.resolve() if args.target else Path.home()) else 0
    if args.action == "resolve":
        cmd_resolve(args.profile)
        return 0
    raise AssertionError(f"hugin profiles: the {args.action!r} command has no handler")
