# Tamper Protection

A rule is only as strong as the agent's inability to switch it off. This file lists the ways gates get bypassed and the protection for each. The enforcement plan picks which apply. The verify stage tries every one.

## Bypass Attempts

| Id | Bypass | Protection |
|----|--------|------------|
| B1 | Inline disable comments (`eslint-disable`, `@ts-ignore`, `@ts-nocheck`) | Ban them by rule. Report unused disable directives. Count existing ones first (see the escape-hatches probe). |
| B2 | Editing the lint, type, or build configuration to loosen a rule | Protected files list. CODEOWNERS entry. A CI job that fails when a protected file changes without approval. |
| B3 | Deleting or renaming a rule file, fixture, or the check script | Same protected files list. The check command verifies its own parts exist. |
| B4 | Skipping local hooks (`git commit --no-verify`) | Treat hooks as convenience only. CI runs the same check command and is the real gate. |
| B5 | Adding a banned dependency | Dependency allow-list and deny-list check inside the check command. |
| B6 | Renaming or moving a file to dodge a glob | Rules match by content or by broad globs, not by exact file name. Layout tests cover the rest. |
| B7 | Putting code outside the checked paths | The check command lints every tracked source path, not a hand-written list. |
| B8 | Making the check command exit 0 on failure | The check command fails closed: a missing tool, crash, or empty result is a failure. |
| B9 | Weakening a rule's level from error to warning | Rule levels live in protected files. The verify stage checks levels. |
| B10 | Changing CI to skip the check | CI definition is in the protected files list and CODEOWNERS. |

## Protected Files

The implement stage records the exact list in its change log. Typical members:

- Lint, type, and build configuration files
- Everything under the hardening tooling folder (rules, fixtures, scripts)
- The CI definition and CODEOWNERS
- The dependency allow-list and deny-list

## Integrity Check

The check command includes a step that compares the protected files against a committed list of hashes. A change without a matching update to that list fails. Updating the list is a visible, reviewable diff.

## Agent Harness Hooks

Some agent harnesses can block writes to chosen files before they happen (for example a pre-tool-use hook that exits with a blocking code when the target path is protected). This gives the agent immediate feedback. It is a convenience, not a gate, because it only exists on one machine. CI stays the source of truth. See `shared/dispatch.md`.

## What This Cannot Stop

- A human who approves a weakened rule.
- Logic errors that no rule describes.
- Anything the coverage matrix marks as level 5 or DEFERRED.

The agent guide says so, so nobody mistakes a passing check for a correct change.
