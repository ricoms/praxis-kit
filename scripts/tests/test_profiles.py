import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        self.target = self.base / "home"
        self.claude = self.target / ".claude"

    def _make_kit(self, name: str) -> Path:
        kit = self.base / name
        _write(kit / "pyproject.toml", '[project]\nname = "hugin"\n')
        _write(kit / "CONSTITUTION.md", "CONSTITUTION.\n")
        _write(kit / "claude" / "CLAUDE.md", "KERNEL.\n")
        _write(kit / "claude" / "rules" / "rule1.md", "Rule one.\n")
        _write(kit / "claude" / "rules" / "rule2.md", "Rule two.\n")
        _skill(kit, "skillA", "Use when doing A.")
        _profile(kit, "base", {"description": "base", "rules": ["rule1.md", "rule2.md"], "skills": ["skillA"]})
        return kit

    def _make_overlay(self, name: str) -> Path:
        overlay = self.base / name
        _write(overlay / "claude" / "rules" / "rule1.md", "Overlay rule one.\n")
        _write(overlay / "claude" / "rules" / "mine.md", "Mine.\n")
        _profile(overlay, "overlay", {"description": "overlay", "rules": ["rule1.md", "mine.md"]})
        return overlay

    def run_install(self, profile_names=("base",), overlay=None, dry_run=False):
        profiles.configure(self.kit, overlay)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = profiles.install(list(profile_names), self.target, dry_run)
        return code, out.getvalue()

    def manifest(self, name="praxis-kit"):
        return json.loads((self.claude / ".kit-manifests" / f"{name}.json").read_text())

    def test_fresh_install_copies_files_and_records_the_manifest(self):
        code, out = self.run_install()
        self.assertEqual(code, 0)
        rule = self.claude / "rules" / "rule1.md"
        self.assertFalse(rule.is_symlink())
        self.assertEqual(rule.read_text(), "Rule one.\n")
        self.assertEqual((self.claude / "rules" / "praxis-kit.md").read_text(), "KERNEL.\n")
        self.assertEqual((self.claude / "CONSTITUTION.md").read_text(), "CONSTITUTION.\n")
        self.assertFalse((self.claude / "CLAUDE.md").exists())
        manifest = self.manifest()
        self.assertNotIn("kit", manifest)
        self.assertEqual(manifest["files"]["skills/skillA/SKILL.md"]["source"], "claude/skills/skillA/SKILL.md")
        self.assertEqual(manifest["files"]["CONSTITUTION.md"]["source"], "CONSTITUTION.md")

    def test_a_kit_under_home_is_recorded_with_a_tilde(self):
        self.assertEqual(profiles._home_relative(Path.home() / "kits" / "praxis-kit"), "~/kits/praxis-kit")
        self.assertEqual(profiles._home_relative(Path("/opt/praxis-kit")), "/opt/praxis-kit")

    def test_an_install_into_home_records_the_kit_path(self):
        with mock.patch.object(Path, "home", return_value=self.target):
            self.run_install()
        self.assertEqual(Path(self.manifest()["kit"]), self.kit)

    def test_an_overlay_named_like_the_shared_kit_is_refused(self):
        self.run_install()
        twin = self._make_overlay("forks/praxis-kit")
        with self.assertRaises(ValueError):
            self.run_install(["overlay"], overlay=twin)
        self.assertEqual((self.claude / "rules" / "praxis-kit.md").read_text(), "KERNEL.\n")

    def test_a_manifest_path_outside_claude_is_rejected_and_nothing_is_deleted(self):
        victim = self.target / "victim.txt"
        _write(victim, "keep me\n")
        digest = profiles._sha256(victim)
        _write(self.claude / ".kit-manifests" / "praxis-kit.json",
               json.dumps({"files": {"../victim.txt": {"source": "x", "sha256": digest}}}))
        with self.assertRaises(ValueError):
            self.run_install()
        self.assertTrue(victim.exists())

    def test_a_manifest_entry_without_a_hash_is_rejected(self):
        _write(self.claude / ".kit-manifests" / "praxis-kit.json", json.dumps({"files": {"rules/rule1.md": {"source": "x"}}}))
        with self.assertRaises(ValueError):
            self.run_install()

    def test_a_file_where_a_directory_belongs_stops_the_install_before_any_change(self):
        self.claude.mkdir(parents=True)
        (self.claude / "CLAUDE.md").symlink_to(self.kit / "claude" / "CLAUDE.md")
        _write(self.claude / "skills", "not a directory\n")
        code, out = self.run_install()
        self.assertEqual(code, 1)
        self.assertIn("REFUSE  skills is in the way", out)
        self.assertTrue((self.claude / "CLAUDE.md").is_symlink())

    def test_a_local_edit_alone_is_kept_without_claiming_the_kit_changed(self):
        self.run_install()
        _write(self.claude / "rules" / "rule1.md", "local edit\n")
        _, out = self.run_install()
        self.assertIn("KEEP    rules/rule1.md (edited here)", out)

    def test_hidden_files_and_caches_in_a_skill_are_not_copied(self):
        _write(self.kit / "claude" / "skills" / "skillA" / ".DS_Store", "x")
        _write(self.kit / "claude" / "skills" / "skillA" / "__pycache__" / "a.pyc", "x")
        self.run_install()
        self.assertFalse((self.claude / "skills" / "skillA" / ".DS_Store").exists())
        self.assertFalse((self.claude / "skills" / "skillA" / "__pycache__").exists())

    def test_dry_run_lists_old_symlinks_and_keeps_them(self):
        self.claude.mkdir(parents=True)
        (self.claude / "CLAUDE.md").symlink_to(self.kit / "claude" / "CLAUDE.md")
        _, out = self.run_install(dry_run=True)
        self.assertIn("UNLINK  CLAUDE.md", out)
        self.assertTrue((self.claude / "CLAUDE.md").is_symlink())

    def test_second_install_changes_nothing(self):
        self.run_install()
        _, out = self.run_install()
        self.assertNotIn("ADD", out)
        self.assertNotIn("UPDATE", out)
        self.assertIn("OK", out)

    def test_an_unedited_file_is_updated_when_the_kit_changes(self):
        self.run_install()
        _write(self.kit / "claude" / "rules" / "rule1.md", "Rule one, revised.\n")
        _, out = self.run_install()
        self.assertIn("UPDATE  rules/rule1.md", out)
        self.assertEqual((self.claude / "rules" / "rule1.md").read_text(), "Rule one, revised.\n")

    def test_a_local_edit_is_kept_when_the_kit_changes(self):
        self.run_install()
        _write(self.claude / "rules" / "rule1.md", "local edit\n")
        _write(self.kit / "claude" / "rules" / "rule1.md", "Rule one, revised.\n")
        _, out = self.run_install()
        self.assertIn("KEEP    rules/rule1.md", out)
        self.assertEqual((self.claude / "rules" / "rule1.md").read_text(), "local edit\n")
        _, out = self.run_install()
        self.assertIn("KEEP    rules/rule1.md", out)

    def test_a_file_the_kit_dropped_is_removed_if_unedited_and_kept_if_edited(self):
        self.run_install()
        _write(self.claude / "rules" / "rule2.md", "local edit\n")
        _profile(self.kit, "base", {"description": "base", "rules": [], "skills": []})
        _, out = self.run_install()
        self.assertIn("REMOVE  rules/rule1.md", out)
        self.assertFalse((self.claude / "rules" / "rule1.md").exists())
        self.assertFalse((self.claude / "skills").exists())
        self.assertIn("KEEP    rules/rule2.md", out)
        self.assertTrue((self.claude / "rules" / "rule2.md").exists())
        self.assertNotIn("rules/rule2.md", self.manifest()["files"])

    def test_an_existing_file_the_kit_did_not_install_stops_the_install(self):
        _write(self.claude / "rules" / "rule1.md", "local content\n")
        code, out = self.run_install()
        self.assertEqual(code, 1)
        self.assertIn("REFUSE  rules/rule1.md", out)
        self.assertFalse((self.claude / "rules" / "rule2.md").exists())
        self.assertFalse((self.claude / ".kit-manifests").exists())
        self.assertEqual((self.claude / "rules" / "rule1.md").read_text(), "local content\n")

    def test_an_existing_identical_file_is_adopted(self):
        _write(self.claude / "rules" / "rule1.md", "Rule one.\n")
        code, _ = self.run_install()
        self.assertEqual(code, 0)
        self.assertIn("rules/rule1.md", self.manifest()["files"])

    def test_a_users_own_claude_md_is_left_alone(self):
        _write(self.claude / "CLAUDE.md", "my own instructions\n")
        code, _ = self.run_install()
        self.assertEqual(code, 0)
        self.assertEqual((self.claude / "CLAUDE.md").read_text(), "my own instructions\n")

    def test_symlinks_from_an_earlier_install_are_replaced_by_copies(self):
        self.claude.mkdir(parents=True)
        (self.claude / "CLAUDE.md").symlink_to(self.kit / "claude" / "CLAUDE.md")
        (self.claude / "skills").mkdir()
        (self.claude / "skills" / "skillA").symlink_to(self.kit / "claude" / "skills" / "skillA")
        code, out = self.run_install()
        self.assertEqual(code, 0)
        self.assertIn("UNLINK  CLAUDE.md", out)
        self.assertFalse((self.claude / "CLAUDE.md").exists())
        self.assertFalse((self.claude / "skills" / "skillA").is_symlink())
        self.assertTrue((self.claude / "skills" / "skillA" / "SKILL.md").is_file())
        self.assertTrue((self.kit / "claude" / "skills" / "skillA" / "SKILL.md").is_file())

    def test_a_symlink_into_another_tree_stops_the_install(self):
        other = self.base / "elsewhere.md"
        _write(other, "elsewhere\n")
        (self.claude / "rules").mkdir(parents=True)
        (self.claude / "rules" / "rule1.md").symlink_to(other)
        code, out = self.run_install()
        self.assertEqual(code, 1)
        self.assertIn("REFUSE  rules/rule1.md is a symlink", out)
        self.assertEqual((self.claude / "rules" / "rule1.md").readlink(), other)

    def test_dry_run_changes_nothing(self):
        code, out = self.run_install(dry_run=True)
        self.assertEqual(code, 0)
        self.assertIn("ADD     rules/rule1.md", out)
        self.assertFalse(self.claude.exists() and any(self.claude.rglob("*")))

    def test_an_overlay_kit_has_its_own_manifest_and_leaves_the_shared_files(self):
        self.run_install()
        code, out = self.run_install(["overlay"], overlay=self.overlay)
        self.assertEqual(code, 0)
        self.assertIn("TAKEN   rules/rule1.md (installed by praxis-kit", out)
        self.assertEqual((self.claude / "rules" / "rule1.md").read_text(), "Rule one.\n")
        self.assertEqual((self.claude / "rules" / "mine.md").read_text(), "Mine.\n")
        overlay = self.manifest("overlay")
        self.assertEqual(set(overlay["files"]), {"rules/mine.md"})
        self.assertNotIn("rules/praxis-kit.md", overlay["files"])

    def test_uninstall_removes_unedited_files_and_keeps_edited_ones(self):
        self.run_install()
        _write(self.claude / "rules" / "rule2.md", "local edit\n")
        profiles.configure(self.kit)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(profiles.uninstall(self.target), 0)
        self.assertIn("KEEP    rules/rule2.md", out.getvalue())
        self.assertFalse((self.claude / "rules" / "rule1.md").exists())
        self.assertFalse((self.claude / "skills").exists())
        self.assertFalse((self.claude / ".kit-manifests").exists())
        self.assertEqual((self.claude / "rules" / "rule2.md").read_text(), "local edit\n")


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
        self.target = self.base / "home"
        with contextlib.redirect_stdout(io.StringIO()):
            profiles.install(["base"], self.target)

    def doctor(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            problems = profiles.cmd_doctor(self.target)
        return problems, out.getvalue()

    def test_a_clean_tree_has_zero_problems(self):
        self.assertEqual(self.doctor()[0], 0)

    def test_a_missing_file_is_a_problem(self):
        (self.target / ".claude" / "rules" / "rule1.md").unlink()
        problems, out = self.doctor()
        self.assertEqual(problems, 1)
        self.assertIn("MISSING   rules/rule1.md", out)

    def test_a_local_edit_is_reported(self):
        _write(self.target / ".claude" / "rules" / "rule1.md", "edited\n")
        problems, out = self.doctor()
        self.assertEqual(problems, 1)
        self.assertIn("EDITED    rules/rule1.md", out)

    def test_a_kit_change_not_yet_installed_is_outdated(self):
        _write(self.kit / "claude" / "rules" / "rule1.md", "Rule one, revised.\n")
        problems, out = self.doctor()
        self.assertEqual(problems, 1)
        self.assertIn("OUTDATED  rules/rule1.md", out)

    def test_a_file_the_kit_removed_is_dropped(self):
        (self.kit / "claude" / "rules" / "rule1.md").unlink()
        problems, out = self.doctor()
        self.assertEqual(problems, 1)
        self.assertIn("DROPPED   rules/rule1.md", out)

    def test_an_untracked_file_is_a_problem(self):
        _write(self.target / ".claude" / "rules" / "extra.md", "not from a kit\n")
        problems, out = self.doctor()
        self.assertEqual(problems, 1)
        self.assertIn("UNTRACKED rules/extra.md", out)

    def test_no_manifest_is_a_problem(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            problems = profiles.cmd_doctor(self.base / "elsewhere")
        self.assertEqual(problems, 1)
        self.assertIn("NO MANIFEST", out.getvalue())


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
