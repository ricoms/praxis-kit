import contextlib
import io
import tempfile
import textwrap
import unittest
from pathlib import Path

from hugin import radar

GOOD = """
[[blip]]
name = "Ratchets"
quadrant = "techniques"
ring = "adopt"
why = "Baselines only shrink"
ref = "docs/ratchet.md"
evidence = "only shrink"
"""


class Radar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "kit"
        (self.root / "docs" / "ai-sdlc").mkdir(parents=True)
        (self.root / "docs" / "ratchet.md").write_text("A baseline may only shrink.\n")
        self.write(GOOD)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, toml):
        (self.root / radar.DATA).write_text(textwrap.dedent(toml))

    def run_radar(self, command):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = radar.run(command, self.root)
        return code, err.getvalue()

    def test_render_then_check_passes(self):
        self.assertEqual(self.run_radar("render"), (0, ""))
        page = (self.root / radar.PAGE).read_text()
        self.assertIn("| Adopt | Ratchets | Baselines only shrink | [`docs/ratchet.md`](../../docs/ratchet.md) |", page)
        self.assertEqual(self.run_radar("check"), (0, ""))

    def test_check_reports_a_stale_page(self):
        self.run_radar("render")
        self.write(GOOD.replace("Baselines only shrink", "Baselines never grow"))
        code, err = self.run_radar("check")
        self.assertEqual(code, 1)
        self.assertIn("radar.md is stale", err)

    def test_check_reports_evidence_the_ref_no_longer_holds(self):
        self.run_radar("render")
        (self.root / "docs" / "ratchet.md").write_text("A baseline may grow.\n")
        code, err = self.run_radar("check")
        self.assertEqual(code, 1)
        self.assertIn("no longer contains 'only shrink'", err)

    def test_problems_names_each_broken_field(self):
        self.write(GOOD + GOOD.replace('ring = "adopt"', 'ring = "maybe"').replace("docs/ratchet.md", "docs/gone.md"))
        code, err = self.run_radar("check")
        self.assertEqual(code, 1)
        self.assertIn("Ratchets: listed twice", err)
        self.assertIn("ring 'maybe' is not one of", err)
        self.assertIn("docs/gone.md does not exist", err)

    def test_render_refuses_to_write_when_a_blip_is_broken(self):
        self.write(GOOD.replace('quadrant = "techniques"', 'quadrant = "gadgets"'))
        code, err = self.run_radar("render")
        self.assertEqual(code, 1)
        self.assertIn("quadrant 'gadgets'", err)
        self.assertFalse((self.root / radar.PAGE).exists())

    def test_load_rejects_a_file_with_no_blip_array(self):
        self.write(GOOD.replace("[[blip]]", "[[blips]]"))
        with self.assertRaises(SystemExit):
            radar.load(self.root)

    def test_problems_rejects_a_ref_outside_the_kit(self):
        (self.root.parent / "outside.md").write_text("A baseline may only shrink.\n")
        self.write(GOOD.replace("docs/ratchet.md", "../outside.md"))
        code, err = self.run_radar("check")
        self.assertEqual(code, 1)
        self.assertIn("../outside.md is outside the kit", err)

    def test_load_rejects_a_blip_that_is_not_a_table_of_strings(self):
        self.write(GOOD.replace('why = "Baselines only shrink"', "why = 3"))
        with self.assertRaises(SystemExit):
            radar.load(self.root)


if __name__ == "__main__":
    unittest.main()
