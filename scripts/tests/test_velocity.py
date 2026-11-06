import contextlib
import io
import json
import re
import tempfile
import unittest

from hugin import cli

S1 = {"title": "Sprint 01", "dueOn": "2026-01-09T00:00:00Z"}
S2 = {"title": "Sprint 02", "dueOn": "2026-01-16T00:00:00Z"}
S3 = {"title": "Sprint 03 · V1", "dueOn": "2026-01-23T00:00:00Z"}


def item(number, milestone, status, estimate=None, actual=None, remaining=None, phase=None, labels=()):
    row = {"content": {"type": "Issue", "number": number}, "status": status, "labels": list(labels)}
    if milestone:
        row["milestone"] = milestone
    for key, value in (("estimate", estimate), ("actual", actual), ("remaining Work", remaining), ("phase", phase)):
        if value is not None:
            row[key] = value
    return row


ITEMS = {"items": [
    item(1, S1, "Done", estimate=2, actual=3, phase="Plan", labels=["type:task"]),
    item(2, S1, "Done", estimate=4, actual=2, phase="Implement", labels=["type:task"]),
    item(3, S1, "Todo", estimate=1, remaining=0.5),
    item(4, S2, "Done", estimate=1, actual=1, phase="Plan", labels=["question"]),
    item(5, S2, "Done", estimate=2),
    item(6, S3, "Todo", estimate=3),
    item(7, S3, "Todo", estimate=2, remaining=1),
    item(8, None, "Done", estimate=5, actual=5),
    item(10, S2, "Done", actual=1.5, labels=["bug", "unplanned"]),
    item(11, S2, "Done", estimate=2, labels=["unplanned"]),
    {"content": {"type": "PullRequest", "number": 9}, "status": "Done", "estimate": 9, "milestone": S1},
]}


def run(*extra):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(ITEMS, f)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli.main(["velocity", "--owner", "o", "--project", "1", "--capacity", "5", "--input", f.name, *extra])
    return out.getvalue()


def rows(text, first_cell):
    return [[c.strip() for c in line.strip("|").split("|")] for line in text.splitlines()
            if line.startswith(f"| {first_cell}")]


class VelocityReading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run("--target", "V1", "--today", "2026-01-12")

    def test_sprint_rows_sum_estimates_and_skip_pull_requests(self):
        table = {r[0]: r[1:] for r in rows(self.out, "Sprint")[1:]}
        self.assertEqual(table["Sprint 01"], ["2026-01-09", "7.0", "6.0", "120%", "0.0", "1"])
        self.assertEqual(table["Sprint 02"], ["2026-01-16", "3.0", "3.0", "60%", "3.5", "0"])
        self.assertEqual(table["Sprint 03 · V1"], ["2026-01-23", "5.0", "0.0", "0%", "0.0", "2"])

    def test_unplanned_work_is_reported_apart_from_planned_work(self):
        header = rows(self.out, "Sprint")[0]
        self.assertIn("Unplanned (d)", header)

    def test_margin_counts_sprints_ahead_and_remaining_work(self):
        line = next(line for line in self.out.splitlines() if line.startswith("Margin"))
        numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", line.split("(due")[1])
        self.assertEqual(numbers[:6], ["2026", "-01", "-23", "2", "5", "10.0"])
        self.assertIn("4.5 d of open work", line)
        self.assertTrue(line.endswith("**+5.5 d**."))

    def test_ratios_by_phase_and_type(self):
        phase = {r[0]: r[1:] for r in rows(self.out, "Plan") + rows(self.out, "Implement")}
        self.assertEqual(phase["Plan (small sample)"], ["2", "1.33", "1.25"])
        self.assertEqual(phase["Implement (small sample)"], ["1", "0.50", "0.50"])
        kinds = {r[0]: r[1:] for r in rows(self.out, "task") + rows(self.out, "question")}
        self.assertEqual(kinds["task (small sample)"], ["2", "0.83", "1.00"])

    def test_coverage_counts_done_estimated_issues(self):
        self.assertIn("4 of 6 done estimated issues have an Actual; 2 missing.", self.out)

    def test_ambiguous_target_is_reported_not_guessed(self):
        self.assertIn("3 found", run("--target", "Sprint 0", "--today", "2026-01-12"))

    def test_zero_capacity_is_rejected_before_dividing(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            run("--capacity", "0")
        self.assertEqual(raised.exception.code, 2)

    def test_capacity_is_required(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            cli.main(["velocity", "--owner", "o", "--project", "1", "--input", "unused.json"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
