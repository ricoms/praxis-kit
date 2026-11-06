"""Render the copier template in several variants and check what the kit claims about it.

Needs copier, uvx, actionlint and shellcheck on PATH, and Docker for the bash 3.2 run.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PRACTICES = Path("docs") / "ai-sdlc" / "practices.md"
SKILLS = Path("claude") / "skills"
ANSWERS_FILE = ".copier-answers.praxis-kit.yml"

BASE = {"project_name": "Demo App", "description": "demo", "tenancy_mode": "single-tenant", "stage": "build",
        "stack_decided": "true"}
VARIANTS: dict[str, dict[str, str]] = {
    "explore": {"stage": "explore", "stack_decided": "false", "team_delivery": "true", "code_owners": "@acme/devs"},
    "explore-stack": {"stage": "explore"},
    "plain": {"stack_decided": "false"},
    "release": {"release_workflow": "true"},
    "team": {"team_delivery": "true", "code_owners": "@acme/devs"},
    "team-release": {
        "team_delivery": "true",
        "code_owners": "@acme/devs",
        "decision_owners": "@acme/architects",
        "release_workflow": "true",
    },
}
PRACTICES_VARIANT = "team-release"
STACK_FREE_JOBS = {"gitleaks", "private-refs"}
CI_RECIPES = {"explore": "test"}
CI_RECIPES_AFTER_EXPLORE = "lint test audit"
CHECKED_TAGS = {"template", "check", "skill"}


def render(src: Path, dest: Path, data: dict[str, str]) -> None:
    args = ["copier", "copy", "--trust", "--defaults", "--quiet"]
    for key, value in {**BASE, **data}.items():
        args += ["--data", f"{key}={value}"]
    subprocess.run([*args, str(src), str(dest)], check=True, capture_output=True, text=True)


def lint(project: Path) -> list[str]:
    errors = []
    workflows = sorted((project / ".github" / "workflows").glob("*.yml"))
    if workflows:
        result = subprocess.run(["actionlint", *map(str, workflows)], capture_output=True, text=True, cwd=project)
        if result.returncode:
            errors.append(f"actionlint:\n{result.stdout}{result.stderr}")
    scripts = sorted(str(p) for p in project.rglob("*.sh"))
    if scripts:
        result = subprocess.run(["shellcheck", *scripts], capture_output=True, text=True, cwd=project)
        if result.returncode:
            errors.append(f"shellcheck:\n{result.stdout}{result.stderr}")
    return errors


def ci_job_ids(ci_yml: Path) -> set[str]:
    jobs: set[str] = set()
    in_jobs = False
    for line in ci_yml.read_text().splitlines():
        if line.startswith("jobs:"):
            in_jobs = True
        elif in_jobs and re.match(r"^\S", line):
            break
        elif in_jobs and (m := re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)):
            jobs.add(m.group(1))
    return jobs


def required_checks_match_ci(project: Path) -> list[str]:
    ruleset = project / ".github" / "rulesets" / "main.json"
    if not ruleset.exists():
        return []
    required = {c["context"] for r in json.loads(ruleset.read_text())["rules"] if r["type"] == "required_status_checks"
                for c in r["parameters"]["required_status_checks"]}
    missing = required - ci_job_ids(project / ".github" / "workflows" / "ci.yml")
    return [f"ruleset requires checks with no job in ci.yml: {sorted(missing)}"] if missing else []


BASH_32_IMAGE = "bash:3.2@sha256:b6252c62fc86114f93f02104a486c71e6569371d95950ea7479a2ffd6b47f16a"
BASH_4_ONLY = re.compile(
    r"\$\{[^}]*(,,?|\^\^?|@[QEPAaUuLk])\}|\b(declare|local|typeset)\s+-\w*[An]|\bmapfile\b|\breadarray\b|\|&|;;&|\bcoproc\b"
)


def docker_running() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def scripts_run_on_bash_32(project: Path) -> list[str]:
    """Developer-machine scripts must work on macOS /bin/bash (3.2); .github/scripts run only on CI runners."""
    rels = (p.relative_to(project) for p in project.rglob("*.sh"))
    scripts = sorted(str(rel) for rel in rels if ".github" not in rel.parts)
    errors = [f"{rel}:{n}: bash 4+ syntax: {line.strip()}" for rel in scripts
              for n, line in enumerate((project / rel).read_text().splitlines(), 1) if BASH_4_ONLY.search(line)]
    if not docker_running():
        if os.environ.get("CI"):
            return [*errors, "docker is required in CI to run scripts under bash 3.2"]
        print("  SKIPPED bash 3.2 run (docker not running)", file=sys.stderr)
        return errors
    run = ["docker", "run", "--rm", "-v", f"{project}:/w", "-w", "/w", BASH_32_IMAGE, "bash"]
    parse = 'for s; do out=$(bash -n "$s" 2>&1) || echo "bash 3.2 cannot parse $s: $out"; done'
    result = subprocess.run([*run, "-c", parse, "_", *scripts], capture_output=True, text=True)
    if result.returncode:
        errors.append(f"bash 3.2 container failed: {result.stderr.strip()}")
    return errors + result.stdout.splitlines()


SOURCE_ENV = 'set -eu; . "$1"; shift; for k; do eval "v=\\${$k-}"; [ -n "$v" ] || echo "$k is empty"; done'


def env_files_source(project: Path) -> list[str]:
    errors = []
    for env in sorted(project.glob(".github/*.env")):
        keys = re.findall(r"^([A-Z_][A-Z0-9_]*)=", env.read_text(), re.M)
        result = subprocess.run(["bash", "-c", SOURCE_ENV, "_", str(env), *keys], capture_output=True, text=True)
        if result.returncode or result.stdout or result.stderr:
            errors.append(f"sourcing {env.relative_to(project)} fails: {(result.stderr + result.stdout).strip()}")
    return errors


DOOR_CASES: list[tuple[str, dict[str, str], set[str]]] = [
    ("docs only", {"docs/notes.md": "x\n"}, set()),
    ("additive migration", {"backend/alembic/versions/0002_add.py": "op.add_column('v', sa.Column('c'))\n"}, set()),
    ("dropping migration", {"backend/alembic/versions/0003_drop.py": "op.drop_column('v', 'c')\n"}, {"data"}),
    ("autogenerated additive migration", {"backend/alembic/versions/0005_add.py": "def upgrade():\n    op.add_column('v', "
     "sa.Column('c'))\n\n\ndef downgrade():\n    op.drop_column('v', 'c')\n"}, set()),
    ("CODEOWNERS", {".github/CODEOWNERS": "* @someone\n"}, {"governance"}),
    ("rails remove_column", {"api/db/migrate/20261027_drop.rb": "def change\n  remove_column :v, :c\nend\n"}, {"data"}),
    ("rails additive with down", {"api/db/migrate/20261027_add.rb":
                                  "def up\n  add_column :v, :c, :text\nend\ndef down\n  remove_column :v, :c\nend\n"}, set()),
    ("django RemoveField", {"app/migrations/0005_x.py": "migrations.RemoveField(model_name='v', name='c')\n"}, {"data"}),
    ("sql drop", {"db/migration/V5__drop.sql": "ALTER TABLE visits DROP COLUMN legacy_ref;\n"}, {"data"}),
    ("sql additive with down", {"migrations/0006.sql": "-- migrate:up\nALTER TABLE v ADD COLUMN c text;\n-- migrate:down\nALTER TABLE v DROP COLUMN c;\n"}, set()),
    ("workflow with a secret", {".github/workflows/x.yml": "env:\n  T: ${{ secrets.T }}\n"}, {"governance"}),
    ("workflow without secrets", {".github/workflows/y.yml": "on: push\n"}, set()),
    ("door workflow", {".github/workflows/doors.yml": "on: push\n"}, {"governance"}),
    ("terraform IAM", {"infra/iam.tf": 'resource "aws_iam_role" "r" {}\n'}, {"effects"}),
    ("door config", {".github/doors.toml": "[data]\nmigrations = []\n"}, {"governance"}),
    ("config loosened with a drop", {".github/doors.toml": "[data]\nmigrations = []\n",
                                     "backend/alembic/versions/0004.py": "op.drop_table('v')\n"}, {"governance", "data"}),
    ("malformed config", {".github/doors.toml": "[data\n"}, {"exit 2"}),
    ("sql rename on its own line", {"db/migration/V6__r.sql": "ALTER TABLE v\n  RENAME COLUMN a TO b;\n"}, {"data"}),
    ("sql delete", {"db/migration/V7__d.sql": "DELETE FROM v WHERE c IS NULL;\n"}, {"data"}),
    ("rails drop_join_table", {"api/db/migrate/1_j.rb": "def change\n  drop_join_table :a, :b\nend\n"}, {"data"}),
    ("rails change_table remove", {"api/db/migrate/2_t.rb": "change_table :v do |t|\n  t.remove :c\nend\n"}, {"data"}),
    ("sql-migrate additive with Down", {"migrations/7.sql": "-- +migrate Up\nALTER TABLE v ADD COLUMN c text;\n"
                                        "-- +migrate Down\nALTER TABLE v DROP COLUMN c;\n"}, set()),
    ("workflow with a token", {".github/workflows/t.yml": "env:\n  T: ${{ github.token }}\n"}, {"governance"}),
    ("terraform role grant", {"infra/sa.tf": 'module "sa" {\n  roles = ["roles/owner"]\n}\n'}, {"effects"}),
]


def doors_classify_behaves(project: Path) -> list[str]:
    script = project / ".github" / "scripts" / "doors.py"
    if not script.exists():
        return []
    errors = []
    env = {**os.environ, "PATH": "/usr/bin:/bin", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}

    def git(repo: Path, *args: str) -> str:
        return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def conditions(repo: Path, base: str) -> set[str]:
        out = subprocess.run([sys.executable, str(script), base, "HEAD"], cwd=repo, env=env, capture_output=True, text=True)
        if out.returncode:
            return {f"exit {out.returncode}"}
        return {r["condition"] for r in json.loads(out.stdout)["reasons"]}

    def commit_all(repo: Path, files: dict[str, str]) -> None:
        for rel, text in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text(text)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "change")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(project, repo)
        (repo / "infra").mkdir(exist_ok=True)
        (repo / "infra" / "bucket.tf").write_text('resource "aws_s3_bucket" "b" {}\nmodule "m" { source = "./m" }\n')
        git(repo, "init", "-q", "-b", "main")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "base")
        base = git(repo, "rev-parse", "HEAD")
        cases = [*DOOR_CASES, ("terraform resource removed", {"infra/bucket.tf": "\n"}, {"effects"}),
                 ("terraform module removed", {"infra/bucket.tf": 'resource "aws_s3_bucket" "b" {}\n'}, {"effects"})]
        for name, files, expected in cases:
            git(repo, "checkout", "-q", "-B", "case", base)
            commit_all(repo, files)
            if (got := conditions(repo, base)) != expected:
                errors.append(f"doors: {name} gave {sorted(got) or 'two-way'}, expected {sorted(expected) or 'two-way'}")
        git(repo, "checkout", "-q", "-B", "case", base)
        git(repo, "mv", ".github/CODEOWNERS", "docs/CODEOWNERS")
        git(repo, "commit", "-q", "-m", "rename")
        if (got := conditions(repo, base)) != {"governance"}:
            errors.append(f"doors: CODEOWNERS renamed away gave {sorted(got) or 'two-way'}, expected ['governance']")
        spec_base = {".github/doors.toml": (repo / ".github/doors.toml").read_text().replace('openapi = ""',
                     'openapi = "openapi.json"'), "openapi.json": "{}\n"}
        spec_cases = [("spec change, oasdiff absent", False, {"openapi.json": '{"openapi": "3.0.0"}\n'}, {"contracts"}),
                      ("spec untouched, oasdiff absent", False, {"docs/notes.md": "x\n"}, set()),
                      ("spec change, internal atomic deploy", True, {"openapi.json": '{"openapi": "3.0.0"}\n'}, set())]
        for name, internal_atomic, change, expected in spec_cases:
            git(repo, "checkout", "-q", "-B", "case", base)
            cfg = spec_base[".github/doors.toml"]
            if internal_atomic:
                cfg = cfg.replace("external_consumers = true", "external_consumers = false")
                cfg = cfg.replace("atomic_frontend_deploy = false", "atomic_frontend_deploy = true")
            commit_all(repo, {**spec_base, ".github/doors.toml": cfg})
            spec_commit = git(repo, "rev-parse", "HEAD")
            commit_all(repo, change)
            if (got := conditions(repo, spec_commit)) != expected:
                errors.append(f"doors: {name} gave {sorted(got) or 'two-way'}, expected {sorted(expected) or 'two-way'}")
    return errors


class _App(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


def smoke_script_behaves(project: Path) -> list[str]:
    script = project / "scripts" / "smoke.sh"
    if not script.exists():
        return ["scripts/smoke.sh was not rendered"] if (project / ".github" / "smoke.txt").exists() else []
    server = HTTPServer(("127.0.0.1", 0), _App)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    wrong = project / "wrong-smoke.txt"
    errors = []
    try:
        if subprocess.run(["bash", str(script), url], cwd=project, capture_output=True).returncode != 0:
            errors.append("smoke.sh failed against an app that answers /health 200 and unknown paths 404")
        wrong.write_text("GET /health 200\nGET /api/v1/x 200")
        if subprocess.run(["bash", str(script), url, str(wrong)], cwd=project, capture_output=True).returncode == 0:
            errors.append("smoke.sh passed although a check expected 200 and got 404")
        wrong.write_text("# no checks\n")
        if subprocess.run(["bash", str(script), url, str(wrong)], cwd=project, capture_output=True).returncode == 0:
            errors.append("smoke.sh passed a file with no checks")
    finally:
        server.shutdown()
        server.server_close()
        wrong.unlink(missing_ok=True)
    return errors


def workflow_step_script(workflow: Path, name: str) -> str:
    lines = workflow.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {name}")
    run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body = []
    for line in lines[run + 1:]:
        if line.strip() and not line.startswith(" " * 10):
            break
        body.append(line[10:])
    return "\n".join(body) + "\n"


FAKE_DOCKER = """#!/usr/bin/env bash
echo "docker $*" >> "$CALL_LOG"
case "$*" in
  *"buildx imagetools inspect"*)
    case "$*" in *"--format {{json .Manifest}}"*) ;; *) echo "unexpected format: $*" >&2; exit 3 ;; esac
    [ -n "${FAKE_NO_CRED_HELPER:-}" ] && { echo 'error getting credentials - err: exec: "docker-credential-x": executable file not found in $PATH' >&2; exit 1; }
    [ -n "${FAKE_DESCRIBE_DENIED:-}" ] && { echo "ERROR: denied: permission denied" >&2; exit 1; }
    [ -n "${FAKE_IMAGE_DIGEST:-}" ] || { echo "ERROR: manifest unknown: not found" >&2; exit 1; }
    echo "{\\"digest\\": \\"$FAKE_IMAGE_DIGEST\\"}" ;;
esac
"""

FAKE_GH = """#!/usr/bin/env bash
case "$*" in
  *'index("success")'*) echo "${FAKE_EVER_SUCCEEDED:-false}" ;;
  *statuses*) echo "${FAKE_DEV_STATE:-}" ;;
  *deployments*) echo "${FAKE_DEPLOYMENT_ID:-}" ;;
esac
"""


def deploy_rollback_behaves(project: Path) -> list[str]:
    workflow = project / ".github" / "workflows" / "release.yml"
    if not workflow.exists():
        return []
    code = "\n".join(line for line in workflow.read_text().splitlines() if not line.lstrip().startswith("#"))
    steps = re.split(r"\n(?=      - )", code)
    unguarded = [s.split("\n")[0].strip() for s in steps
                 if ("scripts/migrate.sh" in s or "alembic upgrade" in s) and "needs.plan.outputs.mode != 'rollback'" not in s]
    if unguarded:
        return [f"release.yml: a rollback would run migrations in {unguarded}; the older code cannot migrate a newer schema"]
    record = workflow_step_script(workflow, "Record the serving revision")
    verify = workflow_step_script(workflow, "Health and customer smoke checks")
    server = HTTPServer(("127.0.0.1", 0), _App)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir, log, out = Path(tmp, "bin"), Path(tmp, "calls.log"), Path(tmp, "output")
            bin_dir.mkdir()
            for tool, fake in (("gh", FAKE_GH), ("docker", FAKE_DOCKER)):
                (bin_dir / tool).write_text(fake)
                (bin_dir / tool).chmod(0o755)
            base = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "CALL_LOG": str(log),
                    "GITHUB_OUTPUT": str(out), "ENVIRONMENT": "dev", "DEPLOY_VARS": '{"API_SERVICE": "api"}',
                    "APP_URL": f"http://127.0.0.1:{server.server_port}/"}

            def run(script: str, **env: str) -> int:
                log.write_text("")
                return subprocess.run(["bash", "-e", "-c", script], cwd=project, env={**base, **env},
                                      capture_output=True).returncode

            plan = workflow_step_script(workflow, "Decide build or promote")
            path = "registry.example/app"
            dev_ok = {"FAKE_DEPLOYMENT_ID": "7", "FAKE_DEV_STATE": "success"}
            image = {"FAKE_IMAGE_DIGEST": "sha256:abc"}
            promote = {"environment=prod", "mode=promote", f"image={path}@sha256:abc"}
            rollback = {"ACTION": "", "DISPATCH_ENVIRONMENT": "prod", "ROLLBACK": "true", "GITHUB_REF_TYPE": "tag",
                        "FAKE_DEPLOYMENT_ID": "7", "FAKE_EVER_SUCCEEDED": "true"}
            plan_cases: list[tuple[str, dict[str, str], set[str] | None]] = [
                ("pre-release", {"ACTION": "prereleased"}, {"environment=dev", "mode=build"}),
                ("final, dev passed", {"ACTION": "released", **dev_ok, **image}, promote),
                ("final, dev failed", {"ACTION": "released", "FAKE_DEPLOYMENT_ID": "7", "FAKE_DEV_STATE": "failure",
                                       **image}, None),
                ("final, image but no dev deployment", {"ACTION": "released", **image}, None),
                ("final, never pre-released", {"ACTION": "released"},
                 {"environment=prod", "mode=build", "skipped_dev=true"}),
                ("final, dev passed but image missing", {"ACTION": "released", **dev_ok}, None),
                ("final, registry permission error", {"ACTION": "released", **dev_ok, "FAKE_DESCRIBE_DENIED": "1"}, None),
                ("dispatch", {"ACTION": "", "DISPATCH_ENVIRONMENT": "dev"}, {"environment=dev", "mode=build"}),
                ("dispatch, rollback false", {"ACTION": "", "DISPATCH_ENVIRONMENT": "dev", "ROLLBACK": "false"},
                 {"environment=dev", "mode=build"}),
                ("rollback", {**rollback, **image}, {"environment=prod", "mode=rollback", f"image={path}@sha256:abc"}),
                ("rollback without an environment", {**rollback, "DISPATCH_ENVIRONMENT": "", **image}, None),
                ("rollback on a branch", {**rollback, "GITHUB_REF_TYPE": "branch", **image}, None),
                ("rollback of a release never deployed", {**rollback, "FAKE_EVER_SUCCEEDED": "false", **image}, None),
                ("rollback of a ref with no released image", rollback, None),
                ("rollback, registry permission error", {**rollback, "FAKE_DESCRIBE_DENIED": "1"}, None),
            ]
            for name, env, expected in plan_cases:
                out.write_text("")
                exit_code = run(plan, **{"IMAGE_REPOSITORY": path, "SHA": "abc123", "DISPATCH_ENVIRONMENT": "", "ROLLBACK": "", **env})
                got = set(out.read_text().split())
                if expected is None and exit_code == 0:
                    errors.append(f"release plan: {name} went ahead ({sorted(got)}) instead of stopping")
                elif expected is not None and (exit_code != 0 or got != expected):
                    errors.append(f"release plan: {name} gave {sorted(got)} (exit {exit_code}), expected {sorted(expected)}")
            reuse = workflow_step_script(workflow, "Reuse this commit's image if it exists")
            for name, env, expected_out, should_pass in [
                ("existing image", image, f"image={path}@sha256:abc", True),
                ("no image", {}, "", True),
                ("registry error", {"FAKE_DESCRIBE_DENIED": "1"}, "", False),
            ]:
                out.write_text("")
                exit_code = run(reuse, **{"IMAGE_REPOSITORY": path, "SHA": "abc123", **env})
                if (exit_code == 0) != should_pass or out.read_text().strip() != expected_out:
                    errors.append(f"release build: reuse with {name} gave {out.read_text().strip()!r} (exit {exit_code})")
            digest_cases = [("existing", image, 0, "sha256:abc"), ("missing", {}, 2, ""),
                            ("registry error", {"FAKE_DESCRIBE_DENIED": "1"}, 1, ""),
                            ("missing credential helper", {"FAKE_NO_CRED_HELPER": "1"}, 1, "")]
            for name, env, expected_code, expected_out in digest_cases:
                result = subprocess.run(["scripts/image-digest.sh", f"{path}:abc123"], cwd=project, capture_output=True,
                                        text=True, env={**base, **env})
                if result.returncode != expected_code or result.stdout.strip() != expected_out:
                    errors.append(f"image-digest.sh: {name} gave {result.stdout.strip()!r} (exit {result.returncode}), "
                                  f"expected {expected_out!r} (exit {expected_code})")
            for command in ("current dev", "release dev reg/app@sha256:abc", "revert dev api-good"):
                if run(f"scripts/deploy.sh {command}") == 0:
                    errors.append(f"deploy.sh: the unwritten slot passed `{command}` instead of failing")
            deploy = project / "scripts" / "deploy.sh"
            stub = deploy.read_text()
            deploy.write_text('#!/usr/bin/env bash\necho "deploy.sh $*" >> "$CALL_LOG"\n'
                              '[ "$1" = current ] && echo api-good\n[ -z "${FAKE_DEPLOY_FAILS:-}" ]\n')
            out.write_text("")
            if run(record) != 0 or out.read_text().strip() != "revision=api-good":
                errors.append(f"rollback target: recorded {out.read_text().strip()!r}, expected the serving revision api-good")
            if run(record, FAKE_DEPLOY_FAILS="1") == 0:
                errors.append("rollback target: a failing `deploy.sh current` did not stop the step")
            smoke = project / ".github" / "smoke.txt"
            original = smoke.read_text()
            if run(verify, PREVIOUS="api-good") != 0 or log.read_text():
                errors.append("deploy checks: passing checks failed or touched the deploy slot")
            smoke.write_text("GET /health 200\nGET /api/v1/x 200\n")
            if run(verify, PREVIOUS="api-good") == 0 or "deploy.sh revert dev api-good" not in log.read_text():
                errors.append("deploy checks: a failing smoke check did not call `deploy.sh revert dev api-good`")
            if run(verify, PREVIOUS="") == 0 or log.read_text():
                errors.append("deploy checks: a first deploy without a previous revision did not fail cleanly")
            smoke.write_text(original)
            deploy.write_text(stub)
    finally:
        server.shutdown()
        server.server_close()
    return errors


LOCAL_HOOKS = "gitleaks"


def precommit_passes(project: Path) -> list[str]:
    env = {**os.environ, "SKIP": LOCAL_HOOKS, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(project, repo, ignore=shutil.ignore_patterns("node_modules", ".venv"))
        subprocess.run(["git", "init", "-q"], cwd=repo, env=env, check=True)
        subprocess.run(["git", "add", "-A"], cwd=repo, env=env, check=True)
        result = subprocess.run(["uvx", "--from", "pre-commit>=4.7,<5", "pre-commit", "run", "--all-files"],
                                cwd=repo, env=env, capture_output=True, text=True)
    return [f"pre-commit fails on a fresh render:\n{result.stdout[-3000:]}"] if result.returncode else []


def private_refs_behave(project: Path) -> list[str]:
    script = project / "scripts" / "private-refs.sh"
    if not script.exists():
        return []
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    errors = []
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(project, repo)

        def run(files: dict[str, str]) -> int:
            for rel, text in files.items():
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text(text)
            subprocess.run(["git", "add", "-A"], cwd=repo, env=env, check=True, capture_output=True)
            return subprocess.run(["bash", "scripts/private-refs.sh"], cwd=repo, env=env, capture_output=True).returncode

        subprocess.run(["git", "init", "-q"], cwd=repo, env=env, check=True)
        link = "see https://acme.slack.com/archives/C123/p456"
        cases = [("clean render", {}, 0), ("slack link", {"docs/notes.md": link + "\n"}, 1),
                 ("marked exception", {"docs/notes.md": link + " private-ref-ok\n"}, 0),
                 ("answers file", {"docs/notes.md": "clean\n", ANSWERS_FILE: f"_src_path: {link}\n"}, 0),
                 ("comments-only patterns", {".github/private-refs.txt": "# none\n", "docs/notes.md": link + "\n"}, 0)]
        for name, files, expected in cases:
            if (code := run(files)) != expected:
                errors.append(f"private-refs: {name} exited {code}, expected {expected}")
    return errors


def dependabot_directories_exist(project: Path) -> list[str]:
    config = project / ".github" / "dependabot.yml"
    if not config.exists():
        return []
    dirs = re.findall(r"^\s+(?:directory: |- )(/[\w/.-]*)\s*$", config.read_text(), re.M)
    return [f"dependabot.yml points at {d}, which the render does not have" for d in dirs
            if not (project / d.lstrip("/")).exists()]


def enforcement_claims(text: str) -> list[tuple[str, str]]:
    """Return (article, segment) pairs from every '- Enforced:' bullet, continuation lines joined."""
    claims = []
    article = "?"
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if m := re.match(r"^### ([IVXLC]+)\.", lines[i]):
            article = m.group(1)
        if lines[i].startswith("- Enforced:"):
            bullet = lines[i][len("- Enforced:"):]
            while i + 1 < len(lines) and lines[i + 1].startswith("  "):
                i += 1
                bullet += " " + lines[i].strip()
            claims += [(article, seg.strip()) for seg in bullet.split(" · ")]
        i += 1
    return claims


def practices_claims_resolve(root: Path, project: Path) -> list[str]:
    errors = []
    for article, segment in enforcement_claims((root / PRACTICES).read_text()):
        tag = re.match(r"^`(\w+)`", segment)
        if not tag or tag.group(1) not in CHECKED_TAGS or "(planned)" in segment:
            continue
        refs = re.findall(r"`([^`]+)`", segment)[1:]
        if not refs:
            errors.append(f"Art. {article}: `{tag.group(1)}` claim names no file or skill: {segment}")
        for ref in refs:
            target = root / SKILLS / ref if tag.group(1) == "skill" else project / ref
            if not target.exists():
                errors.append(f"Art. {article}: {ref} does not exist ({tag.group(1)})")
    return errors


def practices_links_resolve(root: Path) -> list[str]:
    practices = root / PRACTICES
    links = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", practices.read_text())
    return [f"practices.md links to missing {link}" for link in links
            if "://" not in link and not (practices.parent / link).exists()]


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=check", "-c", "user.email=check@localhost", "-c", "commit.gpgsign=false",
                           *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def kit_repo(root: Path, dest: Path) -> Path:
    """A git copy of copier.yml and template/: copier versions a template only from a git repo's root."""
    dest.mkdir()
    for name in ("copier.yml", ".gitignore"):
        shutil.copy2(root / name, dest / name)
    shutil.copytree(root / "template", dest / "template")
    git(dest, "init", "-q")
    git(dest, "add", "-A")
    git(dest, "commit", "-qm", "kit")
    return dest


def update_round_trip(src: Path, tmp: Path) -> list[str]:
    project = tmp / "update"
    head = git(src, "rev-parse", "HEAD")
    try:
        render(src, project, {"stack_decided": "false"})
        answers = project / ANSWERS_FILE
        if not answers.exists():
            return [f"update: no {ANSWERS_FILE} was rendered"]
        recorded = answers.read_text()
        errors = [f"update: {ANSWERS_FILE} does not record {key}: {BASE[key]}" for key in ("tenancy_mode", "stage")
                  if f"{key}: {BASE[key]}" not in recorded]
        git(project, "init", "-q")
        git(project, "add", "-A")
        git(project, "commit", "-qm", "rendered")
        with (project / "README.md").open("a") as f:
            f.write("\nproject edit\n")
        git(project, "commit", "-qam", "project edit")
        marker = "template change for the update check"
        with (src / "template" / "src" / "docs" / "runbooks" / "README.md.jinja").open("a") as f:
            f.write(f"\n{marker}\n")
        git(src, "commit", "-qam", "template change")
        result = subprocess.run(["copier", "update", "--trust", "--defaults", "--quiet", "--vcs-ref", "HEAD",
                                 "--answers-file", ANSWERS_FILE,
                                 "--data", "stack_decided=true", "--data", "release_workflow=true"],
                                cwd=project, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        return [f"update: {' '.join(map(str, exc.cmd))} failed:\n{(exc.stderr or '').strip()}"]
    finally:
        git(src, "reset", "-q", "--hard", head)
    if result.returncode != 0:
        return errors + [f"update: copier update failed:\n{result.stderr.strip()}"]
    if marker not in (project / "docs" / "runbooks" / "README.md").read_text():
        errors.append("update: a template change did not reach the project")
    if "project edit" not in (project / "README.md").read_text():
        errors.append("update: the project's own edit was lost")
    if not (project / ".github" / "workflows" / "release.yml").exists():
        errors.append("update: changing release_workflow on update did not render release.yml")
    if "checks" not in ci_job_ids(project / ".github" / "workflows" / "ci.yml"):
        errors.append("update: changing stack_decided on update did not render CI's checks job")
    return errors


def earlier_release_keeps_stack(src: Path, tmp: Path) -> list[str]:
    """A project rendered before stack_decided existed must not lose its release workflow on `update --defaults`."""
    project = tmp / "earlier-release"
    render(src, project, {"release_workflow": "true"})
    answers = project / ANSWERS_FILE
    answers.write_text("".join(line for line in answers.read_text().splitlines(keepends=True)
                               if not line.startswith("stack_decided:")))
    git(project, "init", "-q")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "rendered before stack_decided")
    result = subprocess.run(["copier", "update", "--trust", "--defaults", "--quiet", "--vcs-ref", "HEAD",
                             "--answers-file", ANSWERS_FILE], cwd=project, capture_output=True, text=True)
    if result.returncode != 0:
        return [f"earlier release project: copier update failed:\n{result.stderr.strip()}"]
    if not (project / ".github" / "workflows" / "release.yml").exists():
        return ["earlier release project: update --defaults removed release.yml"]
    if "stack_decided: true" not in answers.read_text():
        return ["earlier release project: update --defaults did not record stack_decided: true"]
    return []


def declarations_required(src: Path, tmp: Path) -> list[str]:
    errors = []
    for key in ("tenancy_mode", "stage"):
        data = {k: v for k, v in BASE.items() if k != key}
        args = ["copier", "copy", "--trust", "--defaults", "--quiet"]
        for k, v in data.items():
            args += ["--data", f"{k}={v}"]
        result = subprocess.run([*args, str(src), str(tmp / f"no-{key}")], capture_output=True, text=True)
        if result.returncode == 0:
            errors.append(f"rendering without {key} succeeded; it must have no default")
        elif f'Question "{key}" is required' not in result.stderr:
            errors.append(f"rendering without {key} failed for another reason:\n{result.stderr.strip()}")
    return errors


def release_needs_stack(src: Path, tmp: Path) -> list[str]:
    args = ["copier", "copy", "--trust", "--defaults", "--quiet"]
    for key, value in {**BASE, "stack_decided": "false", "release_workflow": "true"}.items():
        args += ["--data", f"{key}={value}"]
    result = subprocess.run([*args, str(src), str(tmp / "release-no-stack")], capture_output=True, text=True)
    if result.returncode == 0:
        return ["rendering release_workflow without stack_decided succeeded; the release needs the stack's slots"]
    if "release_workflow requires stack_decided" not in result.stderr:
        return [f"rendering release_workflow without stack_decided failed for another reason:\n{result.stderr.strip()}"]
    return []


def declarations_rendered(project: Path, answers: dict[str, str]) -> list[str]:
    claude_md = (project / ".claude" / "CLAUDE.md").read_text()
    return [f".claude/CLAUDE.md does not declare {key} `{answers[key]}`" for key in ("tenancy_mode", "stage")
            if f"**`{answers[key]}`**" not in claude_md]


def agreements_cover_constitution(root: Path, project: Path) -> list[str]:
    agreements = project / "docs" / "agreements.md"
    if not agreements.exists():
        return ["docs/agreements.md was not rendered"]
    text = (root / "CONSTITUTION.md").read_text()
    start, end = text.find("### Decisions every team settles"), text.find("## 6.")
    if start < 0 or end < start:
        return ["CONSTITUTION.md: cannot find the 'Decisions every team settles' list before section 6"]
    section = text[start:end]
    decisions = [re.split(r"[:;.]", line[2:])[0].removeprefix("the ") for line in section.splitlines()
                 if line.startswith("- ")]
    lines = agreements.read_text().splitlines()
    headers = [i for i, line in enumerate(lines) if line.startswith("| Decision |")]
    sections = ("## Adjusted working agreements", "## Gaps against the safety floor")
    if not headers or any(section not in lines for section in sections):
        return ["docs/agreements.md needs the decisions table and the sections " + ", ".join(sections)]
    table = lines[headers[0] + 2:]
    rows = [line.split("|")[1:-1] for line in table[:next((i for i, line in enumerate(table) if not line.startswith("|")),
                                                          len(table))]]
    names = {cells[0].strip().lower() for cells in rows}
    errors = [f"docs/agreements.md has no row for '{d}'" for d in decisions if d.lower() not in names]
    errors += [f"docs/agreements.md row '{cells[0].strip()}' must be 'proposed, not yet agreed' with empty choice, date "
               "and decider" for cells in rows
               if [c.strip() for c in cells[2:]] != ["proposed, not yet agreed", "", "", ""]]
    if len(rows) != len(decisions):
        errors.append(f"docs/agreements.md has {len(rows)} rows; CONSTITUTION.md section 5 lists {len(decisions)}")
    return errors


def _job_blocks(workflow: Path) -> dict[str, str]:
    blocks: dict[str, str] = {}
    name = None
    for line in workflow.read_text().splitlines():
        if m := re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line):
            name = m.group(1)
            blocks[name] = ""
        elif name and (line.startswith("    ") or not line.strip()):
            blocks[name] += line + "\n"
        elif name and not line.startswith(" "):
            name = None
    return blocks


def ci_follows_stage(project: Path, stage: str) -> list[str]:
    body = re.search(r"^ci:\n((?:    .*\n)+)", (project / "justfile").read_text(), re.M)
    loop = re.search(r"for recipe in (.*); do", body.group(1)) if body else None
    expected = CI_RECIPES.get(stage, CI_RECIPES_AFTER_EXPLORE)
    if not loop or loop.group(1) != expected:
        return [f"justfile: `just ci` at {stage} runs {loop.group(1) if loop else 'nothing'!r}, expected {expected!r}"]
    return []


def ci_needs_no_stack(project: Path) -> list[str]:
    ci = project / ".github" / "workflows" / "ci.yml"
    if not ci.exists():
        return []
    return [f"ci.yml: renders the {job} job before the stack is decided, so a fresh render cannot pass CI"
            for job in sorted(ci_job_ids(ci) - STACK_FREE_JOBS)]


def ci_slots_wired(project: Path) -> list[str]:
    ci = project / ".github" / "workflows" / "ci.yml"
    if not ci.exists():
        return []
    errors = []
    jobs = _job_blocks(ci)
    checks = jobs.get("checks", "")
    if not re.search(r"^\s+- run: just ci\s*$", checks, re.M):
        errors.append("ci.yml: the checks job does not run `just ci`")
    if "uses: ./.github/actions/toolchain" not in checks:
        errors.append("ci.yml: the checks job does not install the stack through .github/actions/toolchain")
    if not re.search(r"^ci:", (project / "justfile").read_text(), re.M):
        errors.append("justfile: no `ci` recipe for CI's checks job to run")
    if not (project / ".github" / "actions" / "toolchain" / "action.yml").exists():
        errors.append(".github/actions/toolchain/action.yml was not rendered")
    builds = []
    if (project / ".github" / "workflows" / "release.yml").exists():
        builds = [("ci.yml", "image"), ("release.yml", "build")]
    elif "image" in jobs:
        errors.append("ci.yml: renders an image job without a release workflow, so a project with no image stays red")
    for workflow, job in builds:
        block = _job_blocks(project / ".github" / "workflows" / workflow).get(job, "")
        if not re.search(r"^\s+run: scripts/build-image\.sh \S+", block, re.M):
            errors.append(f"{workflow}: the {job} job does not build with scripts/build-image.sh, so CI and the release can differ")
    return errors


def slots_fail_until_written(project: Path) -> list[str]:
    errors = []
    build = project / "scripts" / "build-image.sh"
    if build.exists() and subprocess.run([str(build), "app:test"], cwd=project, capture_output=True).returncode == 0:
        errors.append("scripts/build-image.sh: the unwritten slot passed instead of failing")
    justfile = (project / "justfile").read_text()
    for recipe in ("lint", "test", "audit"):
        body = re.search(rf"^{recipe}:\n((?:    .*\n)+)", justfile, re.M)
        script = "\n".join(line[4:].lstrip("@") for line in body.group(1).splitlines()) if body else ""
        if not script or subprocess.run(["bash", "-e", "-c", script], cwd=project, capture_output=True).returncode == 0:
            errors.append(f"justfile: the unwritten `{recipe}` recipe does not fail")
    setup = project / ".github" / "actions" / "target-setup" / "action.yml"
    if setup.exists() and "exit 1" not in setup.read_text():
        errors.append(".github/actions/target-setup: the unwritten slot does not fail")
    return errors


def labels_carry_kinds(root: Path, project: Path) -> list[str]:
    labels = project / ".github" / "labels.tsv"
    if not labels.exists():
        return []
    rule = (root / "claude" / "rules" / "engineering" / "labelling-issues.md").read_text()
    kind_line = next((line for line in rule.splitlines() if "gets a **kind**" in line), "")
    kinds = re.findall(r"`([a-z]+)`", kind_line)
    if not kinds:
        return ["labelling-issues.md: cannot find the kind list"]
    names = {line.split("\t")[0] for line in labels.read_text().splitlines() if line.strip()}
    errors = [f".github/labels.tsv has no `{k}` label, which the labelling rule requires as a kind" for k in kinds
              if k not in names]
    forms = [*(project / ".github" / "ISSUE_TEMPLATE").glob("*.yml"), *(project / ".github" / "ISSUE_TEMPLATE").glob("*.yaml")]
    for form in sorted(f for f in forms if f.stem != "config"):
        m = re.search(r"^labels:\s*\[(.*)\]", form.read_text(), re.M)
        used = re.findall(r"""["']([^"']+)["']""", m.group(1)) if m else []
        if not set(used) & set(kinds):
            errors.append(f"{form.relative_to(project)} files issues with no kind label ({', '.join(kinds)})")
    return errors


def runbooks_indexed(project: Path) -> list[str]:
    runbooks = project / "docs" / "runbooks"
    index = (runbooks / "README.md").read_text()
    names = [p.name + ("/" if p.is_dir() else "") for p in sorted(runbooks.iterdir()) if p.name != "README.md"]
    errors = [f"docs/runbooks/README.md does not list {n}" for n in names if f"]({n})" not in index]
    links = re.findall(r"\]\(([^)#]+)\)", index)
    return errors + [f"docs/runbooks/README.md links {link}, which was not rendered" for link in links
                     if not (runbooks / link).exists()]


def run(root: Path) -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        src = kit_repo(root, Path(tmp) / "kit")
        failures += declarations_required(src, Path(tmp)) + release_needs_stack(src, Path(tmp))
        failures += earlier_release_keeps_stack(src, Path(tmp))
        update_errors = update_round_trip(src, Path(tmp))
        failures += update_errors
        print(f"update: {'FAIL' if update_errors else 'ok'}")
        for name, data in VARIANTS.items():
            project = Path(tmp) / name
            try:
                render(src, project, data)
            except subprocess.CalledProcessError as exc:
                failures.append(f"[{name}] render failed:\n{exc.stderr}")
                continue
            errors = lint(project) + required_checks_match_ci(project) + env_files_source(project)
            errors += dependabot_directories_exist(project) + slots_fail_until_written(project)
            errors += doors_classify_behaves(project) + smoke_script_behaves(project) + deploy_rollback_behaves(project)
            answers = {**BASE, **data}
            errors += private_refs_behave(project) + declarations_rendered(project, answers)
            errors += agreements_cover_constitution(root, project)
            errors += runbooks_indexed(project) + labels_carry_kinds(root, project) + ci_follows_stage(project, answers["stage"])
            errors += ci_slots_wired(project) if answers["stack_decided"] == "true" else ci_needs_no_stack(project)
            errors += scripts_run_on_bash_32(project) + precommit_passes(project)
            if name == PRACTICES_VARIANT:
                errors += practices_claims_resolve(root, project) + practices_links_resolve(root)
            failures += [f"[{name}] {e}" for e in errors]
            print(f"{name}: {'FAIL' if errors else 'ok'}")
    for failure in failures:
        print(failure, file=sys.stderr)
    return 1 if failures else 0
