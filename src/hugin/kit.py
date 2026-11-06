"""Find the praxis-kit checkout that hugin works on, wherever hugin itself is installed."""

import argparse
import tomllib
from pathlib import Path


def add_root_argument(p: argparse.ArgumentParser) -> None:
    p.add_argument("--root", type=Path, help="the kit's checkout; found by walking up from the current directory when omitted")


def is_kit(path: Path) -> bool:
    manifest = path / "pyproject.toml"
    if not manifest.is_file():
        return False
    try:
        project = tomllib.loads(manifest.read_text()).get("project", {})
    except tomllib.TOMLDecodeError:
        return False
    return isinstance(project, dict) and project.get("name") == "hugin"


def find_root(start: Path) -> Path:
    start = start.resolve()
    for path in (start, *start.parents):
        if is_kit(path):
            return path
    raise SystemExit(f"hugin: {start} is not inside a praxis-kit checkout; run hugin from the kit's checkout or pass --root")


def given_root(path: Path) -> Path:
    root = path.resolve()
    if not is_kit(root):
        raise SystemExit(f"hugin: --root {path} is not a praxis-kit checkout: it has no pyproject.toml for hugin")
    return root


def root(given: Path | None) -> Path:
    return given_root(given) if given else find_root(Path.cwd())
