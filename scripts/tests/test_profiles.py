import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hugin import cli, profiles


class ToolGrantCheck(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "claude"
        (self.root / "agents").mkdir(parents=True)
        (self.root / "skills" / "probe").mkdir(parents=True)
        profiles.configure(Path(tmp.name))

    def skill(self, frontmatter):
        (self.root / "skills" / "probe" / "SKILL.md").write_text(f"---\nname: probe\n{frontmatter}\n---\n# Probe\n")

    def agent(self, frontmatter):
        (self.root / "agents" / "probe.md").write_text(
            f"---\nname: probe\n{frontmatter}\n---\nFollow ~/.claude/skills/probe/SKILL.md\n"
        )

    def gaps(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            errors = profiles.check_agent_tool_grants()
        return errors, out.getvalue()

    def test_a_tool_only_in_requires_tools_is_a_gap(self):
        self.skill("allowed-tools: Read Bash(git log *)\nmetadata:\n  requires-tools: Write Edit")
        self.agent('tools: ["Read", "Bash", "Edit"]\nmodel: sonnet')
        errors, out = self.gaps()
        self.assertEqual(errors, 1)
        self.assertIn("declares Write", out)

    def test_inline_tools_followed_by_another_key_grant_their_last_tool(self):
        self.skill("allowed-tools: Read\nmetadata:\n  requires-tools: Write Bash")
        self.agent("tools: Read, Write, Bash\nmodel: sonnet")
        self.assertEqual(self.gaps()[0], 0)

    def test_tools_as_a_yaml_list(self):
        self.skill("metadata:\n  requires-tools: Write Bash")
        self.agent("tools:\n  - Read\n  - Write\n  - Bash\nmodel: sonnet")
        self.assertEqual(self.gaps()[0], 0)

    def test_requires_tools_as_a_folded_scalar(self):
        self.skill("metadata:\n  requires-tools: >-\n    Write Edit\n    Bash\n  tags:\n    - Probe")
        self.agent("tools: [Read, Write, Edit]")
        errors, out = self.gaps()
        self.assertEqual(errors, 1)
        self.assertIn("declares Bash", out)

    def test_a_top_level_requires_tools_is_reported_not_skipped(self):
        self.skill("requires-tools: Write")
        self.agent("tools: Read")
        errors, out = self.gaps()
        self.assertEqual(errors, 1)
        self.assertIn("MISPLACED requires-tools", out)


def _write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _skill(kit: Path, name: str, description: str) -> Path:
    return _write(
        kit / "claude" / "skills" / name / "SKILL.md",
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n",
    )


def _profile(kit: Path, name: str, data: dict) -> Path:
    return _write(kit / "profiles" / f"{name}.json", json.dumps(data))


class ResolveTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.kit = Path(tmp.name) / "kit"
        _write(self.kit / "pyproject.toml", '[project]\nname = "hugin"\n')
        _profile(self.kit, "base", {"description": "base", "rules": ["r1.md"], "skills": ["A", "B"]})
        _profile(self.kit, "child", {"description": "child", "extends": "base", "skills": ["B", "C"]})
        profiles.configure(self.kit)

    def test_extends_merges_parent_then_child_and_dedupes(self):
        merged = profiles.resolve("child")
        self.assertEqual(merged["skills"], ["A", "B", "C"])
        self.assertEqual(merged["rules"], ["r1.md"])

    def test_circular_extends_raises_value_error(self):
        _profile(self.kit, "a", {"description": "a", "extends": "b"})
        _profile(self.kit, "b", {"description": "b", "extends": "a"})
        with self.assertRaises(ValueError):
            profiles.resolve("a")

    def test_missing_profile_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            profiles.resolve("does-not-exist")

    def test_a_non_object_profile_raises_value_error(self):
        _write(self.kit / "profiles" / "array.json", "[]")
        with self.assertRaises(ValueError):
            profiles.resolve("array")


class InstallTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.kit = self._make_kit("kit")
        self.overlay = self._make_overlay("overlay")

    def _make_kit(self, name: str) -> Path:
        kit = self.base / name
        _write(kit / "pyproject.toml", '[project]\nname = "hugin"\n')
        _write(kit / "CONSTITUTION.md", "CONSTITUTION.\n")
        _write(kit / "claude" / "CLAUDE.md", "KERNEL.\n")
        _write(kit / "claude" / "rules" / "rule1.md", "Rule one.\n")
        _skill(kit, "skillA", "Use when doing A.")
        _profile(kit, "base", {"description": "base", "rules": ["rule1.md"], "skills": ["skillA"]})
        return kit

    def _make_overlay(self, name: str) -> Path:
        overlay = self.base / name
        _write(overlay / "claude" / "rules" / "rule1.md", "Overlay rule one.\n")
        _profile(overlay, "overlay", {"description": "overlay", "rules": ["rule1.md"]})
        return overlay

    def target(self, name: str) -> Path:
        return self.base / name

    def install(self, profile_names, target, kit=None, overlay=None):
        profiles.configure(kit or self.kit, overlay)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            profiles.install(profile_names, target)
        return out.getvalue()

    def test_fresh_install_links_items_into_the_kit(self):
        target = self.target("home1")
        out = self.install(["base"], target)
        self.assertIn("LINK", out)
        rule_link = target / ".claude" / "rules" / "rule1.md"
        skill_link = target / ".claude" / "skills" / "skillA"
        self.assertTrue(rule_link.is_symlink())
        self.assertEqual(rule_link.resolve(), (self.kit / "claude" / "rules" / "rule1.md").resolve())
        self.assertTrue(skill_link.is_symlink())
        self.assertTrue((target / ".claude" / "CLAUDE.md").is_symlink())
        self.assertTrue((target / ".claude" / "CONSTITUTION.md").is_symlink())

    def test_second_install_is_idempotent(self):
        target = self.target("home2")
        self.install(["base"], target)
        out2 = self.install(["base"], target)
        self.assertNotIn("LINK", out2)
        self.assertIn("OK", out2)

    def test_an_existing_real_file_is_skipped_and_left_untouched(self):
        target = self.target("home3")
        rule_path = target / ".claude" / "rules" / "rule1.md"
        _write(rule_path, "local content\n")
        out = self.install(["base"], target)
        self.assertIn("SKIP", out)
        self.assertFalse(rule_path.is_symlink())
        self.assertEqual(rule_path.read_text(), "local content\n")

    def test_a_dangling_wrong_symlink_is_replaced(self):
        target = self.target("home4")
        rule_path = target / ".claude" / "rules" / "rule1.md"
        rule_path.parent.mkdir(parents=True)
        rule_path.symlink_to(target / "nowhere.md")
        out = self.install(["base"], target)
        self.assertIn("LINK", out)
        self.assertTrue(rule_path.is_symlink())
        self.assertEqual(rule_path.resolve(), (self.kit / "claude" / "rules" / "rule1.md").resolve())

    def test_a_symlink_to_a_different_existing_target_is_taken_and_left_alone(self):
        target = self.target("home5")
        other = self.base / "elsewhere.md"
        _write(other, "elsewhere\n")
        rule_path = target / ".claude" / "rules" / "rule1.md"
        rule_path.parent.mkdir(parents=True)
        rule_path.symlink_to(other)
        out = self.install(["base"], target)
        self.assertIn("TAKEN", out)
        self.assertEqual(rule_path.readlink(), other)

    def test_an_overlay_kit_does_not_link_claude_md_or_constitution(self):
        target = self.target("home6")
        self.install(["overlay"], target, kit=self.kit, overlay=self.overlay)
        self.assertFalse((target / ".claude" / "CLAUDE.md").exists())
        self.assertFalse((target / ".claude" / "CONSTITUTION.md").exists())

    def test_an_overlay_item_already_owned_by_the_shared_kit_is_taken(self):
        target = self.target("home7")
        self.install(["base"], target, kit=self.kit)
        shared_link = target / ".claude" / "rules" / "rule1.md"
        original_target = shared_link.readlink()
        out = self.install(["overlay"], target, kit=self.kit, overlay=self.overlay)
        self.assertIn("TAKEN", out)
        self.assertEqual(shared_link.readlink(), original_target)


class BudgetTests(unittest.TestCase):
    DESC = "Use when doing A for budget testing purposes in the suite."

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.kit = Path(tmp.name) / "kit"
        _write(self.kit / "pyproject.toml", '[project]\nname = "hugin"\n')
        _write(self.kit / "claude" / "CLAUDE.md", "KERNEL CONTENT FOR BUDGET TEST.\n")
        _write(self.kit / "claude" / "rules" / "rule_a.md", "RULE A TEXT.\n")
        _write(self.kit / "claude" / "rules" / "rule_b.md", "RULE B HAS MORE TEXT IN IT.\n")
        _skill(self.kit, "skillA", self.DESC)
        _write(
            self.kit / "claude" / "skills" / "skillB" / "SKILL.md",
            "---\nname: skillB\ndescription: >-\n  Use when doing A for budget\n"
            "  testing purposes in the suite.\n---\n# Skill B\n",
        )
        _profile(
            self.kit, "base",
            {"description": "base", "rules": ["rule_a.md", "rule_b.md"], "skills": ["skillA", "skillB"]},
        )
        profiles.configure(self.kit)
        kernel_size = (self.kit / "claude" / "CLAUDE.md").stat().st_size
        rules_size = sum(
            (self.kit / "claude" / "rules" / n).stat().st_size for n in ("rule_a.md", "rule_b.md")
        )
        self.total = kernel_size + rules_size + 2 * len(self.DESC)

    def budget(self, **kwargs):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = profiles.cmd_budget(**kwargs)
        return code, out.getvalue()

    def test_a_folded_description_matches_the_equivalent_single_line(self):
        folded = profiles._frontmatter_description(self.kit / "claude" / "skills" / "skillB" / "SKILL.md")
        inline = profiles._frontmatter_description(self.kit / "claude" / "skills" / "skillA" / "SKILL.md")
        self.assertEqual(folded, self.DESC)
        self.assertEqual(folded, inline)

    def test_total_is_kernel_plus_rules_plus_descriptions(self):
        code, out = self.budget(limit=10**9)
        self.assertEqual(code, 0)
        self.assertIn(f"{self.total:>7}  TOTAL", out)

    def test_over_limit_returns_1(self):
        code, out = self.budget(limit=self.total - 1)
        self.assertEqual(code, 1)
        self.assertIn("OVER BUDGET", out)

    def test_within_limit_returns_0(self):
        code, out = self.budget(limit=self.total)
        self.assertEqual(code, 0)
        self.assertIn("Within budget", out)

    def test_run_budget_with_no_limit_under_an_overlay_kit_returns_2(self):
        overlay = self.kit.parent / "overlay"
        _write(overlay / "profiles" / "empty.json", "{}")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["profiles", "--root", str(self.kit), "--kit", str(overlay), "budget"])
        self.assertEqual(code, 2)


class DoctorTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.kit = self.base / "kit"
        _write(self.kit / "pyproject.toml", '[project]\nname = "hugin"\n')
        _write(self.kit / "CONSTITUTION.md", "CONSTITUTION.\n")
        _write(self.kit / "claude" / "CLAUDE.md", "KERNEL.\n")
        _write(self.kit / "claude" / "rules" / "rule1.md", "Rule one.\n")
        _skill(self.kit, "skillA", "Use when doing A.")
        _profile(self.kit, "base", {"description": "base", "rules": ["rule1.md"], "skills": ["skillA"]})
        profiles.configure(self.kit)

    def target(self, name: str) -> Path:
        return self.base / name

    def install(self, target):
        with contextlib.redirect_stdout(io.StringIO()):
            profiles.install(["base"], target)

    def doctor(self, target):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            problems = profiles.cmd_doctor(target)
        return problems, out.getvalue()

    def test_a_clean_tree_has_zero_problems(self):
        target = self.target("clean")
        self.install(target)
        problems, out = self.doctor(target)
        self.assertEqual(problems, 0)
        self.assertIn("OK", out)

    def test_dangling_when_the_repo_artifact_is_removed(self):
        target = self.target("dangling")
        self.install(target)
        (self.kit / "claude" / "rules" / "rule1.md").unlink()
        problems, out = self.doctor(target)
        self.assertEqual(problems, 1)
        self.assertIn("DANGLING", out)

    def test_foreign_symlink_is_reported_but_not_counted_as_a_problem(self):
        target = self.target("foreign")
        self.install(target)
        other = self.base / "elsewhere.md"
        _write(other, "elsewhere\n")
        (target / ".claude" / "rules" / "foreign.md").symlink_to(other)
        problems, out = self.doctor(target)
        self.assertEqual(problems, 0)
        self.assertIn("FOREIGN", out)

    def test_a_real_copy_of_a_repo_artifact_is_a_problem(self):
        target = self.target("copy")
        _write(target / ".claude" / "rules" / "rule1.md", "a real copy\n")
        problems, out = self.doctor(target)
        self.assertEqual(problems, 1)
        self.assertIn("COPY", out)

    def test_an_untracked_file_is_a_problem(self):
        target = self.target("untracked")
        _write(target / ".claude" / "rules" / "extra.md", "not in the repo\n")
        problems, out = self.doctor(target)
        self.assertEqual(problems, 1)
        self.assertIn("UNTRACKED", out)

    def test_missing_constitution_when_the_kernel_is_linked(self):
        target = self.target("missing-constitution")
        kernel = target / ".claude" / "CLAUDE.md"
        kernel.parent.mkdir(parents=True)
        kernel.symlink_to(self.kit / "claude" / "CLAUDE.md")
        problems, out = self.doctor(target)
        self.assertEqual(problems, 1)
        self.assertIn("MISSING", out)


class LintDescriptionsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.kit = Path(tmp.name) / "kit"
        profiles.configure(self.kit)

    def lint(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            profiles.lint_descriptions()
        return out.getvalue()

    def test_warns_when_a_description_is_over_the_length_limit(self):
        _skill(self.kit, "toolong", "Use when " + "x" * 400)
        out = self.lint()
        self.assertIn("WARN description toolong", out)
        self.assertIn("chars (max", out)

    def test_warns_when_a_description_has_no_use_trigger(self):
        _skill(self.kit, "notrigger", "A short description for testing a missing trigger word.")
        out = self.lint()
        self.assertIn("WARN description notrigger", out)
        self.assertIn('no "Use when', out)

    def test_silent_for_a_compliant_description(self):
        _skill(self.kit, "good", "Use when testing that no warning appears for compliant text.")
        out = self.lint()
        self.assertEqual(out, "")


class CliTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.kit = self.base / "kit"
        _write(self.kit / "pyproject.toml", '[project]\nname = "hugin"\n')
        _profile(self.kit, "base", {"description": "base", "rules": ["r1.md"]})
        _profile(self.kit, "child", {"description": "child", "extends": "base", "rules": ["r2.md"]})

    def test_resolve_prints_the_merged_profile_as_json(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["profiles", "--root", str(self.kit), "resolve", "child"])
        self.assertEqual(code, 0)
        merged = json.loads(out.getvalue())
        self.assertEqual(merged["rules"], ["r1.md", "r2.md"])

    def test_a_kit_dir_without_a_profiles_folder_is_rejected(self):
        not_a_kit = self.base / "not-a-kit"
        not_a_kit.mkdir()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            cli.main(["profiles", "--root", str(self.kit), "--kit", str(not_a_kit), "resolve", "base"])
        self.assertEqual(raised.exception.code, 2)

    def test_an_unknown_profile_exits_with_its_name_not_a_traceback(self):
        with self.assertRaises(SystemExit) as raised:
            cli.main(["profiles", "--root", str(self.kit), "resolve", "nope"])
        self.assertIn("nope", str(raised.exception.code))

    def test_a_non_object_profile_fails_list_and_validate_with_its_path(self):
        _write(self.kit / "profiles" / "array.json", "[]")
        for action in ("list", "validate"):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as raised:
                cli.main(["profiles", "--root", str(self.kit), action])
            self.assertIn("array.json", str(raised.exception.code))


if __name__ == "__main__":
    unittest.main()
