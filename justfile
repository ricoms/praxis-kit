# praxis-kit — profile-driven install of skills, agents, commands, rules

set shell := ["bash", "-euo", "pipefail", "-c"]

repo_dir := justfile_directory()
profiles := "uv run --no-dev --project " + repo_dir + " hugin profiles --root " + repo_dir

python := env_var_or_default("PYTHON", "uv run python")

# Scripts not yet moved into src/hugin; mypy --strict counts their errors against scripts/mypy-baseline.txt
unmoved := "scripts/check_template.py"

# List recipes
default:
    @just --list

# the template's doors.py needs tomllib, stdlib only from 3.11 — fails with the version found, not a traceback
check-python:
    #!/usr/bin/env bash
    set -euo pipefail
    {{python}} <<'EOF'
    import sys
    need = (3, 11)
    if sys.version_info[:2] < need:
        have = "%d.%d.%d" % sys.version_info[:3]
        sys.stderr.write(
            "error: {{python}} is %s, but this recipe needs Python >= %d.%d (the template's doors.py imports tomllib)\n"
            % (have, *need)
        )
        sys.exit(1)
    EOF

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
check-template: check-python
    {{python}} scripts/check_template.py

# Fixture tests for the kit's scripts (scripts/tests)
test:
    {{python}} -m unittest discover -s scripts/tests

# mypy --strict: a gate on src/hugin, and a ratchet on the unmoved scripts whose error count may only fall
typecheck:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run mypy
    baseline=$(cat scripts/mypy-baseline.txt)
    found=$({ uv run mypy --strict --python-version 3.13 {{unmoved}} 2>&1 || true; } | sed -n 's/^Found \([0-9]*\) error.*/\1/p')
    found=${found:-0}
    if (( found > baseline )); then
        echo "error: the unmoved scripts have $found mypy --strict errors, above the baseline of $baseline in scripts/mypy-baseline.txt" >&2
        exit 1
    fi
    if (( found < baseline )); then
        echo "error: the unmoved scripts now have $found mypy --strict errors; lower scripts/mypy-baseline.txt from $baseline to $found" >&2
        exit 1
    fi

# Everything CI runs (.github/workflows/ci.yml), in the same order; run it before every push
check: check-python
    {{profiles}} validate
    {{profiles}} budget
    uv run hugin radar check
    {{python}} -m unittest discover -s scripts/tests
    {{just_executable()}} --justfile {{justfile()}} typecheck
    {{python}} scripts/check_template.py

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

# Two-way drift check: repo artifacts vs installed ~/.claude tree
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

# Dry run: show what would be installed for a profile (no symlinks)
install-dry PROFILE:
    @{{profiles}} resolve {{PROFILE}}

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

# Re-apply all registered projects (symlinks refresh from current repo state)
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

# ── Status / cleanup ───────────────────────────────────────────

# Show what's currently symlinked in ~/.claude/
status:
    #!/usr/bin/env bash
    CLAUDE="$HOME/.claude"
    for kind in skills agents commands rules; do
        echo "=== ~/.claude/$kind ==="
        if [ -d "$CLAUDE/$kind" ]; then
            for item in "$CLAUDE/$kind"/*; do
                [ -e "$item" ] || continue
                if [ -L "$item" ]; then
                    target=$(readlink "$item")
                    case "$target" in
                        "{{repo_dir}}"/*) echo "  LINK $(basename "$item") → praxis-kit" ;;
                        *) echo "  LINK $(basename "$item") → $target" ;;
                    esac
                else
                    echo "  COPY $(basename "$item") (not a symlink)"
                fi
            done
        fi
    done

# Remove stale symlinks pointing into this repo (or into ROOT, another kit) to non-existent items
clean-stale ROOT=repo_dir:
    #!/usr/bin/env bash
    set -euo pipefail
    CLAUDE="$HOME/.claude"
    REPO="$(cd "{{invocation_directory()}}" && cd "{{ROOT}}" && pwd -P)"
    cleaned=0
    for kind in skills agents commands rules; do
        for item in "$CLAUDE/$kind"/*; do
            [ -L "$item" ] || continue
            target=$(readlink "$item")
            case "$target" in
                "$REPO"/*)
                    if [ ! -e "$target" ]; then
                        rm "$item"
                        echo "  CLEAN $(basename "$item")"
                        cleaned=$((cleaned + 1))
                    fi ;;
            esac
        done
    done
    [ $cleaned -gt 0 ] && echo "Removed $cleaned stale symlinks." || echo "No stale symlinks."
