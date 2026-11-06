"""Classify a pull request as a one-way or two-way door from .github/doors.toml.

Usage: doors.py BASE HEAD [--config .github/doors.toml]
The config is read from BASE, so a change cannot exempt itself by editing it.
Prints JSON {"one_way": bool, "reasons": [{"condition", "path", "why"}]}.
Exit 0 on any classification, 2 when the base or head config is unreadable or malformed.
"""

from __future__ import annotations

import argparse
import functools
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

SECRET_WORKFLOW = re.compile(
    r"secrets\.|github\.token|GITHUB_TOKEN|:\s*write\b|write-all|pull_request_target|^\s*environment:", re.M
)
REMOVED_TF_BLOCK = re.compile(r'^\s*(resource|module)\s+"')
SELF = (".github/doors.toml", ".github/scripts/doors.py", ".github/scripts/doors.sh", ".github/workflows/doors.yml")


@functools.lru_cache
def glob_regex(pattern: str) -> re.Pattern[str]:
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(f"^{out}$")


def matches(path: str, globs: list[str]) -> bool:
    return any(glob_regex(g).match(path) for g in globs)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changed(base: str, head: str) -> list[str]:
    out = git("diff", "--no-renames", "--name-status", f"{base}...{head}")
    return [line.split("\t")[-1] for line in out.splitlines() if line]


def diff_lines(base: str, head: str, path: str, sign: str) -> list[str]:
    out = git("diff", "--no-renames", "-U0", f"{base}...{head}", "--", path).splitlines()
    return [line[1:] for line in out if line.startswith(sign) and not line.startswith(sign * 3)]


def show(rev: str, path: str) -> str | None:
    result = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def upgrade_lines(rev: str, path: str, downgrade: re.Pattern[str]) -> set[str]:
    return set(downgrade.split(show(rev, path) or "", maxsplit=1)[0].splitlines())


def openapi_breaking(base: str, head: str, spec: str) -> str | None:
    old, new = show(git("merge-base", base, head).strip(), spec), show(head, spec)
    if new is None:
        return f"{spec} named in doors.toml does not exist (counted as breaking)"
    if old is None or old == new:
        return None
    if shutil.which("oasdiff") is None:
        return "spec changed and oasdiff is not installed (counted as breaking)"
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp, "base" + Path(spec).suffix), Path(tmp, "head" + Path(spec).suffix)
        a.write_text(old)
        b.write_text(new)
        result = subprocess.run(["oasdiff", "breaking", str(a), str(b), "--fail-on", "ERR"], capture_output=True)
    return "breaking API change (oasdiff)" if result.returncode else None


class ConfigError(ValueError):
    pass


def section(cfg: dict[str, object], name: str) -> dict[str, object]:
    value = cfg.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a table")
    return value


def strings(sec: dict[str, object], key: str) -> list[str]:
    value = sec.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{key} must be a list of strings")
    return [str(v) for v in value]


def flag(sec: dict[str, object], key: str, default: bool) -> bool:
    value = sec.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{key} must be true or false")
    return value


def validate(cfg: dict[str, object]) -> None:
    data, contracts, effects = section(cfg, "data"), section(cfg, "contracts"), section(cfg, "effects")
    for sec, key in [(data, "migrations"), (data, "destructive"), (contracts, "paths"), (effects, "paths"),
                     (effects, "calls"), (effects, "terraform"), (section(cfg, "governance"), "paths")]:
        strings(sec, key)
    for pattern in strings(data, "destructive") + strings(effects, "calls") + strings(effects, "terraform"):
        re.compile(pattern)
    marker = data.get("downgrade_marker", "")
    if not isinstance(marker, str):
        raise ConfigError("downgrade_marker must be a regex string")
    re.compile(marker)
    if not isinstance(contracts.get("openapi", ""), str):
        raise ConfigError("openapi must be a path string")
    flag(contracts, "external_consumers", True)
    flag(contracts, "atomic_frontend_deploy", False)


def classify(base: str, head: str, cfg: dict[str, object]) -> list[dict[str, str]]:
    data, contracts = section(cfg, "data"), section(cfg, "contracts")
    effects, governance = section(cfg, "effects"), section(cfg, "governance")
    destructive = [re.compile(p) for p in strings(data, "destructive")]
    calls = [re.compile(p) for p in strings(effects, "calls")]
    tf_patterns = [re.compile(p) for p in strings(effects, "terraform")]
    marker = data.get("downgrade_marker", "")
    if not isinstance(marker, str):
        raise ConfigError("downgrade_marker must be a regex string")
    downgrade = re.compile(marker or r"(?!)", re.M)
    migrations, contract_paths = strings(data, "migrations"), strings(contracts, "paths")
    effect_paths, governance_paths = strings(effects, "paths"), strings(governance, "paths")
    spec = contracts.get("openapi", "")
    if not isinstance(spec, str):
        raise ConfigError("openapi must be a path string")
    external = flag(contracts, "external_consumers", True)
    internal_atomic = not external and flag(contracts, "atomic_frontend_deploy", False)
    reasons: list[dict[str, str]] = []

    def add(condition: str, path: str, why: str) -> None:
        reasons.append({"condition": condition, "path": path, "why": why})

    for path in changed(base, head):
        added = diff_lines(base, head, path, "+")
        if matches(path, migrations):
            upgrade = upgrade_lines(head, path, downgrade)
            hit = next((m.group(0) for p in destructive for line in added if line in upgrade and (m := p.search(line))),
                       None)
            if hit:
                add("data", path, f"migration reshapes or drops data ({hit})")
        if matches(path, contract_paths):
            add("contracts", path, "declared contract")
        if matches(path, effect_paths):
            add("effects", path, "declared effect path")
        hit = next((m.group(0) for p in calls for line in added if (m := p.search(line))), None)
        if hit:
            add("effects", path, f"new effectful call ({hit})")
        if path.endswith(".tf"):
            if any(p.search(line) for p in tf_patterns for line in added):
                add("effects", path, "IAM change")
            if any(REMOVED_TF_BLOCK.match(line) for line in diff_lines(base, head, path, "-")):
                add("effects", path, "Terraform resource or module removed")
        if path in SELF or matches(path, governance_paths):
            add("governance", path, "governance file")
        elif path.startswith(".github/workflows/"):
            content = show(head, path) or show(base, path) or ""
            if SECRET_WORKFLOW.search(content):
                add("governance", path, "workflow holding secrets, a token or write permissions")

    if spec and not internal_atomic:
        why = openapi_breaking(base, head, spec)
        if why:
            add("contracts", spec, why)
    return reasons


def load(rev: str, path: str) -> dict[str, object] | None:
    text = show(rev, path)
    return None if text is None else tomllib.loads(text)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("head")
    p.add_argument("--config", default=".github/doors.toml")
    args = p.parse_args(argv)
    try:
        cfg = load(args.base, args.config)
        if cfg is None:
            cfg = tomllib.loads(Path(args.config).read_text())
        head_cfg = load(args.head, args.config)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"::error::cannot read {args.config}: {exc}", file=sys.stderr)
        return 2
    try:
        if head_cfg is not None:
            validate(head_cfg)
        reasons = classify(args.base, args.head, cfg)
    except (ConfigError, re.error) as exc:
        print(f"::error::{args.config}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"one_way": bool(reasons), "reasons": reasons}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
