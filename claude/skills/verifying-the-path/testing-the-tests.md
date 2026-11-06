# Testing the tests

The loop in `SKILL.md` proves one check. This proves a **change**: that its tests would fail if any decision
the spec makes were wrong, that they do not break when nothing is wrong, and that the values an operator will
need to change are where an operator can change them. Run it once a change is built and green, before review.

Three passes, in order. Each ends in fixes on the change, then the pass is run again.

## 1 · Mutation pass, tied to the spec

**Default: hand-picked mutants and a short script.** No dependency, any stack, about ten minutes for a slice.

1. **List the change's decisions**, from its spec and plan: each boundary, guard, branch, refusal, and each thing
   stored or not stored. Tag each with the requirement that makes it (`FR-5`, `S-1`, a contract line).
2. **Write one mutant per decision**: the smallest edit that makes it wrong. `>` to `>=`, a guard dropped, a
   write removed, a header never sent, a path left out of an allowlist, an inactive state read as active, a
   window changed by one unit.
3. **Run the change's own specs against each mutant** on a throwaway copy (a worktree or a container that is
   discarded), restoring the file after each. A mutant the specs fail on is **killed**; one they pass is a
   **survivor**. Record the baseline as green first: a red baseline kills everything and proves nothing.

```ruby
# mutants: [file, exact text, replacement, "FR-n what it breaks"]
SPECS = "spec/models/thing_spec.rb spec/services/thing"  # the change's own specs
JSON.parse(File.read("mutants.json")).each do |file, from, to, name|
  src = File.read(file)
  next puts("#{name}: NOT APPLIED") unless src.scan(from).size == 1
  File.write(file, src.sub(from) { to })
  killed = !system("bin/rspec #{SPECS} --fail-fast > /dev/null 2>&1")
  File.write(file, src)
  puts "#{name}: #{killed ? "killed" : "SURVIVED"}"
end
```

4. **Triage every survivor**, using its requirement tag:

| Survivor | Means | Do |
|---|---|---|
| Breaks a specified behaviour | the requirement has no test that holds it | add the test, re-run that mutant |
| Changes nothing observable | an equivalent mutant (an exact-instant boundary, say) | record it as equivalent; leave it |
| Mutates code no requirement asks for | dead code, or behaviour the spec never named | delete it, or take it to the spec |

5. **After wiring**, when a later step connects the change to its callers, put the old call back and watch the
   new request or integration specs fail. A spec that still passes with the old call is testing something else.

**Options.** A team that wants mutation continuous picks a tool per stack and runs it on the changed files in CI:
Stryker (JavaScript, TypeScript, C#; Apache-2.0), mutmut (Python), cargo-mutants (Rust), pitest (JVM). For Ruby,
`mutant` needs a commercial licence for closed-source code, so the hand pass stays the default there. A tool
replaces the listing, never the triage.

## 2 · Brittleness

A test is brittle when it fails for a reason that is not a defect, or passes for a reason that is not the
behaviour. Read the change's specs for:

| Smell | Example | Fix |
|---|---|---|
| A stub of an internal | `allow(Model).to receive(:finder)` to force a branch | build the state that takes the branch |
| An assertion on how, not what | a private call counted, a query string matched | assert at the boundary: the request made, the row written, the answer given |
| One fixture shape | an allowlist proven on the one fixture that lacks the optional keys | run the property over every fixture, including the ones carrying optional data |
| A vacuous pass | a "served while the upstream fails" test that passes because the old path still succeeds | make every other path fail too, so only the one under test can answer |
| A constant copied into the test | the test computes the expected value the way the code does | state the value from the spec, with its citation |

## 3 · Values that belong in configuration

A literal in code is one of two things:

- **A constant**: set by a contract, spec or protocol, where changing it means changing that document first.
  A slug pattern, a header's size cap, a status vocabulary. Keep it named, citing its source. Making it
  configurable lets someone break the contract by flipping a setting.
- **Configuration**: a value an operator may need to change without a release. Limits, thresholds, windows,
  cooldowns, timeouts, anything tied to traffic, an incident or an environment. Move it to the project's one
  configuration place, with its default, the default's source, and an environment override where the project
  overrides its other limits that way. A load test that must raise a limit for its window is the usual proof.

Find candidates with the stack's linter where it has one (ESLint `no-magic-numbers`, Pylint
`magic-value-comparison`); otherwise search the change for duration and number literals outside the
configuration directory. A project that wants this enforced adds a rule to its own static checks.

After moving a value, re-run the mutants that changed it: a test that pinned the old literal may now read the
configuration and pass whatever it holds.

## Companion: code smells

Before the passes, run the stack's smell detectors on the changed files, once, without adding them as
dependencies: reek and flay for Ruby, the linter's complexity rules elsewhere. Fix what names a real problem
(duplicated construction, a flag passed only to choose a branch, logic sitting with the wrong object); leave
what only restates the linter's size limits.

## Report

Per pass: the count (mutants killed of total; survivors by kind; values moved), each fix with its commit, and
what was not covered. "Equivalent" and "not covered" are results, said as such.
