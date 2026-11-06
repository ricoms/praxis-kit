---
name: verifying-the-path
description: >-
  Prove a check or change works on the real target: put the defect back and
  watch it fail; mutate a change against its spec. Use before calling any check,
  test or change done.
metadata:
  tags:
    - verification
    - testing
    - ci-cd
---

# Verifying the path

A green check proves only that it ran. It counts as verified when it has been shown to **fail on the real target
with the defect present**, and to pass once the defect is gone. Team practices Article XII.

## When

- Before saying a check, test, gate, hook, workflow step or fix works.
- When a new test passes on its first run.
- After a review changes a check: the change may have made it vacuous.

## The loop

1. **Name the defect** the check exists to catch, in one sentence, and **the real target**: the rendered project,
   the live repository, the deployed environment, the account the data lives in.
2. **Run the check on the real target as it is.** It should pass. If the target cannot be reached, say so; do not
   substitute a nearby one silently.
3. **Put the defect back** on a copy: revert the fix, remove the guard, break the comparison, feed the input that
   caused the bug. The check must **fail, with a message that names the defect**. If it still passes, it does not
   test what it claims; fix the check before anything else.
4. **Restore and run again.** It passes.
5. **Exercise the path, not the piece.** Run what CI or the deploy runs — the step's own script taken from the
   rendered workflow, the hook as the hook manager installs it, the image as the registry would serve it. Fake an
   external tool only at the boundary, with output shaped like the real one. When the boundary cannot be faked
   (permissions, platform behaviour), use a throwaway sandbox and remove it afterwards.
6. **Read the primary record**: the run's conclusion, the step's exit code, the log line — not a summary or a
   badge. "Not run", "skipped" and "empty" are not "passed". Confirm which account or connector you are reading
   before trusting an empty result.
7. **Report** in four lines: what was verified, on which target; which defect was put back and how the check
   failed; what remains unverified and why; what would close it.

## A whole change

One check is proved by the loop above. A change — a slice, a feature, a fix with several decisions — is proved
by three passes in [testing-the-tests.md](testing-the-tests.md): mutants tied to the spec's requirements, the
tests' brittleness, and the literals that belong in configuration. Run them once the change is green, before
review.

## Traps

| Trap | What it looks like | Guard |
|---|---|---|
| A pipe hides the exit code | `check \| tail -1` exits 0 while the check failed | `set -o pipefail`, or capture the exit code before piping |
| A vacuous pass | the expected result equals the default, so a broken check still matches | include a case whose expected result differs from the default |
| A fake that encodes a guess | the fake tool returns an error text nobody has seen from the real one | mark it as inferred in the report; prefer recorded real output |
| The check reads the change under test | config or code loaded from the PR lets the PR exempt itself | load rules from the base, and add a case that loosens them |
| Success recorded over a failure | a deployment or status says success while a step failed | assert on the step result, not the summary |
| The wrong account | a connector or CLI signed in elsewhere returns nothing | check identity first; treat zero hits as an error |
| One-case confidence | the happy path passes once | one case per branch of the decision, each mutation caught |

## Done means

The check failed for the defect it targets, on the real target or a stated stand-in, and the report says what was
not verified. Anything less is reported as unverified, not as done.
