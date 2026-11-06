# praxis-kit — profile-driven install of skills, agents, commands, rules

set shell := ["bash", "-euo", "pipefail", "-c"]

repo_dir := justfile_directory()
profiles := "uv run --no-dev --project " + repo_dir + " hugin profiles --root " + repo_dir

python := env_var_or_default("PYTHON", "uv run python")

# List recipes
default:
    @just --list

# ── Profile management ─────────────────────────────────────────

# List all profiles + descriptions
list-profiles:
    @{{profiles}} list

# Show what a profile resolves to (after extends chain)
resolve PROFILE:
    @{{profiles}} resolve {{PROFILE}}

# Validate that every artifact belongs to >=1 profile (+ description lint)
validate:
    @{{profiles}} validate

# Always-on token budget: CLAUDE.md + rules + skill descriptions (ratchet — limit in src/hugin/profiles.py BUDGET_LIMIT)
budget:
    @{{profiles}} budget

# Render the copier template variants; lint them; check ruleset vs ci.yml, practices and constitution claims
check-template:
    uv run hugin check-template

# Fixture tests for hugin's commands (scripts/tests)
test:
    uv run python -m unittest discover -s scripts/tests

# mypy --strict on src/hugin
typecheck:
    uv run mypy

# Everything CI runs (.github/workflows/ci.yml), in the same order; run it before every push
check:
    {{profiles}} validate
    {{profiles}} budget
    uv run hugin radar check
    uv run python -m unittest discover -s scripts/tests
    {{just_executable()}} --justfile {{justfile()}} typecheck
    uv run hugin check-template

# ── References ─────────────────────────────────────────────────

# Download every arXiv source named in docs/references/*.md (PDFs stay untracked)
references-fetch:
    #!/usr/bin/env bash
    set -euo pipefail
    cd docs/references
    for note in *.md; do
        id=$(awk 'NR==1 && $0!="---" {exit} /^---$/ && NR>1 {exit} sub(/^id: arXiv:/, "")' "$note")
        [ -n "$id" ] || continue
        pdf="${note%.md}.pdf"
        [ -f "$pdf" ] && continue
        curl -fsSL -o "$pdf" "https://arxiv.org/pdf/$id"
        echo "fetched $pdf"
    done

# Index the constitution, references and team practices for qmd search
docs-index:
    qmd collection show praxis-kit >/dev/null 2>&1 || qmd collection add . --name praxis-kit --mask '{CONSTITUTION.md,docs/references/*.md,docs/ai-sdlc/**/*.md}'
    qmd update
    qmd embed || { echo "qmd embed failed: keyword search (qmd search) works, semantic search (qmd query) does not" >&2; exit 1; }

# Compare the installed ~/.claude tree with its manifest and with this checkout
doctor:
    @{{profiles}} doctor

# ── Install ────────────────────────────────────────────────────

# Install all profiles globally (~/.claude/) — full set
install:
    @{{profiles}} install

# Install specific profile(s) globally
install-only *PROFILES:
    @{{profiles}} install {{PROFILES}}

# Install profile(s) into a specific project
# Usage: just install-project DIR PROFILE [PROFILE...]
install-project DIR *PROFILES:
    @{{profiles}} install-project {{DIR}} {{PROFILES}}

# Show what installing a profile would change, and change nothing
install-dry PROFILE:
    @{{profiles}} install --dry-run {{PROFILE}}

# Remove this kit's unedited files from ~/.claude (or from DIR/.claude)
uninstall DIR='':
    @{{profiles}} uninstall {{DIR}}

# ── Project registry ───────────────────────────────────────────

# Show registered projects (from projects.json)
projects:
    #!/usr/bin/env bash
    if [ ! -f projects.json ]; then
        echo "No projects.json yet. Copy projects.example.json to projects.json and edit."
        exit 0
    fi
    {{python}} -c "
    import json
    d = json.load(open('projects.json'))
    for name, p in d.get('projects', {}).items():
        profiles = ', '.join(p['profiles'])
        notes = f' — {p.get(\"notes\", \"\")}' if p.get('notes') else ''
        print(f'{name:<24} {profiles}{notes}')
        print(f'  {p[\"path\"]}')
    "

# Re-apply all registered projects (copies refresh from current repo state)
projects-sync-all:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -f projects.json ]; then
        echo "No projects.json — copy from projects.example.json"
        exit 1
    fi
    {{python}} -c "
    import json, subprocess
    d = json.load(open('projects.json'))
    repo = '{{repo_dir}}'
    profiles = ['uv', 'run', '--no-dev', '--project', repo, 'hugin', 'profiles', '--root', repo]
    for name, p in d.get('projects', {}).items():
        print(f'=== {name} ===')
        cmd = profiles + ['install-project', p['path']] + p['profiles']
        subprocess.run(cmd, check=True)
        print()
    "

# Add a project to projects.json (creates the file from example if missing)
# Usage: just projects-add NAME PATH PROFILES_COMMA_SEP
projects-add NAME PATH PROFILES:
    #!/usr/bin/env bash
    set -euo pipefail
    [ -f projects.json ] || cp projects.example.json projects.json
    {{python}} -c "
    import json
    d = json.load(open('projects.json'))
    d.setdefault('projects', {})['{{NAME}}'] = {
        'path': '{{PATH}}',
        'profiles': '{{PROFILES}}'.split(','),
    }
    json.dump(d, open('projects.json', 'w'), indent=2)
    "
    @echo "Added {{NAME}} to projects.json"

# Remove a project from projects.json
projects-remove NAME:
    #!/usr/bin/env bash
    set -euo pipefail
    [ -f projects.json ] || (echo "No projects.json"; exit 1)
    {{python}} -c "
    import json
    d = json.load(open('projects.json'))
    d.get('projects', {}).pop('{{NAME}}', None)
    json.dump(d, open('projects.json', 'w'), indent=2)
    "
    @echo "Removed {{NAME}} from projects.json"
