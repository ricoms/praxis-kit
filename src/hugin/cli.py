import argparse
from importlib.metadata import version

from hugin import check_template, kit, profiles, radar, snapshot, velocity


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hugin", description="praxis-kit's tooling.")
    parser.add_argument("--version", action="version", version=f"hugin {version('hugin')}")
    commands = parser.add_subparsers(dest="command", required=True)
    radar_cmd = commands.add_parser("radar", help="render docs/ai-sdlc/radar.md, or check it is current and its evidence holds")
    kit.add_root_argument(radar_cmd)
    radar_cmd.add_argument("action", choices=["render", "check"])
    velocity_cmd = commands.add_parser("velocity", help="read delivery velocity from a project board")
    velocity.add_arguments(velocity_cmd)
    snapshot_cmd = commands.add_parser(
        "snapshot", help="collect a dated repository snapshot, or report on one",
        description=snapshot.__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    snapshot.add_arguments(snapshot_cmd)
    profiles_cmd = commands.add_parser(
        "profiles", help="resolve and install the kit's profiles, and check the kit",
        description=profiles.__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    profiles.add_arguments(profiles_cmd)
    template_cmd = commands.add_parser(
        "check-template", help="render the copier template's variants and check what the kit claims about them",
        description=check_template.__doc__)
    kit.add_root_argument(template_cmd)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "radar":
        return radar.run(args.action, kit.root(args.root))
    if args.command == "velocity":
        return velocity.run(args)
    if args.command == "snapshot":
        return snapshot.run(args)
    if args.command == "profiles":
        return profiles.run(args)
    if args.command == "check-template":
        return check_template.run(kit.root(args.root))
    raise AssertionError(f"hugin: the {args.command!r} command has no handler in cli.main")
