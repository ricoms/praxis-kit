# Hand-over

What the team does when this repository passes to the client. Run the steps in order: every step but the last
needs the team's access, and the last one ends it. Keep the issue or PR that did each step as the record.

1. Delete `.copier-answers.praxis-kit.yml` and commit the removal. It names the kit's repository, which the
   client's repository must not, and template updates end there. In the same commit, remove the lines that still
   name the file: the Status section of `.claude/CLAUDE.md`, and the `copier update` command in
   `docs/agreements.md` if a row still shows it. Verify: `git ls-files '.copier-answers*'` prints nothing, and
   `git grep -n copier-answers -- .claude docs/agreements.md` finds nothing.
2. Hand over the secret custodian role to someone on the client's side, or, if nobody takes it over, rotate every
   secret the team's custodian could read. `docs/raci.md` lists roles only, so the client lead confirms the new
   holder in the hand-over issue rather than in that file. Verify: the hand-over issue names who holds the role now,
   or `docs/runbooks/rotations.log` has a dated entry for each secret rotated.
3. Remove or repoint what points at the team's own systems.
   - The board: transfer the team's project board to the client, or have the client create its own with
     `scripts/board/bootstrap-project.sh`.
   - Reviewers: replace the team's handles in `.github/CODEOWNERS` with the client's own reviewers.

   Verify: `.github/CODEOWNERS` names no team handle, and the client can open the board it will use.
4. Write every private name the team used to `.git/info/private-refs`, one extended regex per line. Include other
   repositories, internal tools, Slack or email domains, and each team member's name and handle. That file is
   never committed, so the names do not reach the client. Join the patterns into one, leaving out blank and comment
   lines: `pat=$(grep -vE '^[[:space:]]*(#|$)' .git/info/private-refs | paste -sd'|' -)`. Then run three searches,
   each case-insensitive:
   - `git grep -nIiE "$pat"` lists matching lines in the current files. Fix every one. A line that must keep a
     name, such as an ADR's deciders or a past `rotations.log` entry, stays if the architecture decider agrees.
   - `git log --all -i -E -G "$pat" --format='%h %s' --name-only` lists the commits whose changes add or remove a
     name, with their files.
   - `git log --all -i -E --grep "$pat" --format='%h %s'` lists the commits whose messages name one, including
     trailers such as `Co-Authored-By`.

   A transfer carries the whole history. Commit authors are not searched, because they stay unless the history is
   rewritten. If the history searches list a commit beyond the lines kept above, the architecture decider chooses
   between rewriting the history and handing over a fresh repository. Issues and pull requests travel with a
   transfer too, so search them for the same names. Verify: the searches list only what the architecture decider
   chose to keep, and `docs/raci.md` names no person.
5. Move access per the joining-and-leaving agreement (`CONSTITUTION.md` §5) and the access practice
   (`CONSTITUTION.md` §4: "Access granted on joining and removed on leaving"). Transfer the repository to the
   client's organization, or grant the client's own owners admin on it. Then remove every team member's access to
   the repository, the cloud accounts and any other tool the client does not keep. Owners of the organization that
   holds the repository keep access whatever its collaborator list says. Verify: the repository's collaborators
   and teams, the owners of the organization that holds it, and each cloud project's access list name only people
   who still need them.
