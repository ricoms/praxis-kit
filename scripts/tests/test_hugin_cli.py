import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from hugin import cli, kit

RADAR = """
[[blip]]
name = "Ratchets"
quadrant = "techniques"
ring = "adopt"
why = "Baselines only shrink"
ref = "docs/ratchet.md"
evidence = "only shrink"
"""


class KitRoot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.kit = self.base / "kit"
        (self.kit / "docs" / "ai-sdlc").mkdir(parents=True)
        (self.kit / "pyproject.toml").write_text('[project]\nname = "hugin"\n')
        (self.kit / "docs" / "ratchet.md").write_text("A baseline may only shrink.\n")
        (self.kit / "docs" / "ai-sdlc" / "radar.toml").write_text(RADAR)

    def tearDown(self):
        self.tmp.cleanup()

    def test_find_root_walks_up_from_a_nested_directory(self):
        nested = self.kit / "docs" / "ai-sdlc"
        self.assertEqual(kit.find_root(nested), self.kit.resolve())

    def test_find_root_fails_outside_the_kit(self):
        with self.assertRaises(SystemExit) as raised:
            kit.find_root(self.base)
        self.assertIn("--root", str(raised.exception))

    def test_a_pyproject_for_another_project_is_not_the_kit(self):
        other = self.base / "other"
        other.mkdir()
        (other / "pyproject.toml").write_text('[project]\nname = "something-else"\n')
        self.assertFalse(kit.is_kit(other))
        with self.assertRaises(SystemExit):
            kit.given_root(other)

    def test_main_runs_radar_on_the_given_root(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(["radar", "--root", str(self.kit), "render"]), 0)
            self.assertEqual(cli.main(["radar", "--root", str(self.kit), "check"]), 0)
        self.assertEqual(err.getvalue(), "")

    def test_main_finds_the_root_from_the_current_directory(self):
        cli.main(["radar", "--root", str(self.kit), "render"])
        before = Path.cwd()
        os.chdir(self.kit / "docs")
        try:
            self.assertEqual(cli.main(["radar", "check"]), 0)
        finally:
            os.chdir(before)

    def test_main_requires_a_command(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            cli.main([])
        self.assertEqual(raised.exception.code, 2)

    def test_velocity_runs_outside_the_kit_and_passes_its_arguments_through(self):
        items = self.base / "items.json"
        items.write_text('{"items": []}')
        before = Path.cwd()
        os.chdir(self.base)
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                code = cli.main(["velocity", "--owner", "o", "--project", "1", "--capacity", "5", "--input", str(items)])
        finally:
            os.chdir(before)
        self.assertEqual(code, 0)
        self.assertIn("## Velocity", out.getvalue())

    def test_velocity_help_shows_velocity_options(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            cli.main(["velocity", "--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--capacity", out.getvalue())

    def test_velocity_rejects_root_because_it_does_not_use_the_kit(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            cli.main(["velocity", "--root", "/nonexistent", "--owner", "o", "--project", "1", "--capacity", "5"])
        self.assertEqual(raised.exception.code, 2)

    def test_check_template_refuses_a_root_that_is_not_the_kit(self):
        with self.assertRaises(SystemExit) as raised:
            cli.main(["check-template", "--root", str(self.base)])
        self.assertIn("not a praxis-kit checkout", str(raised.exception))

    def test_radar_rejects_unknown_arguments(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            cli.main(["radar", "--root", str(self.kit), "check", "--owner", "o"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
