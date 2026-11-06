# Security policy

## Reporting a vulnerability

Report a vulnerability privately through GitHub: on the repository's **Security** tab, choose **Report a
vulnerability**. Don't open a public issue, pull request or discussion about it.

Include what is affected, how to reproduce it, and what an attacker could do with it. The maintainers acknowledge the
report on the advisory, agree a fix and a disclosure date with you there, and credit you in the advisory unless you
ask not to be named.

## What is in scope

- The kit's tooling: `scripts/`, `src/hugin/`, `install.sh` and the `justfile`.
- The template under `template/`, especially the workflows and scripts it renders into other projects, because a flaw
  there reaches every project rendered from it.
- Agent rules and skills that could lead an agent to leak a secret, bypass a check, or act outside its scope.

Vulnerabilities in a project rendered from the template, in code the project wrote itself, belong to that project.

## Supported versions

The kit has no releases yet. Fixes land on `main`, and a rendered project picks them up with `copier update`.
