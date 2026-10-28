# Verification Protocol

How to try to break the gates. The verifier runs in a fresh context with only the change log, the branch, and the bypass list.

## Setup

1. Read the change log. Note the worktree path, the check command, and the rule table.
2. Create a disposable worktree at the hardened branch in a system temp folder: `git worktree add --detach <temp> <branch>`. Detached, because git will not check out a branch that another worktree already holds. Install dependencies with the lockfile.
3. Confirm the check command passes on the clean worktree. If it does not, stop with verdict FAIL.

All further edits happen in the disposable worktree. The user's working tree and the implement worktree are never touched.

## Per-Rule Test

For each implemented rule in the change log:

1. Write a short snippet that violates the rule, in a path the check covers.
2. Run the check command. Expected: non-zero exit, and the rule's message in the output.
3. Record `caught` or `missed`, the command, and the exit code.
4. Restore the file (`git checkout -- .` and remove new files).
5. Write a short compliant snippet of the same kind. Expected: the check passes. Record false positives.

Pass means caught and no false positive. Anything else is a defect.

## Bypass Tests

Try each bypass in `../../../shared/tamper-protection.md` that the change log says is covered. For each:

1. Apply the bypass in the disposable worktree.
2. Run the check command, and where relevant the CI-equivalent command or the integrity check.
3. Record `blocked` if some gate fails, `bypassed` if everything passes.
4. Record `not covered` for bypasses the plan explicitly did not protect. These are gaps, not failures, but they appear in the report.
5. Restore the worktree.

Local hooks do not count as blocking for B4. The check command run directly must still fail.

## Verdict

| Verdict | Condition |
|---------|-----------|
| PASS | Every rule caught, no false positives, no covered bypass succeeded |
| FAIL | Any rule missed, any false positive, or any covered bypass succeeded |

A FAIL returns the user to the implement stage with the report as the fix list.

## Report Shape

| Heading | Content |
|---------|---------|
| `## Verdict` | PASS or FAIL, with date and the branch sha |
| `## Rule Results` | Table: rule id, caught or missed, false positive yes or no, command |
| `## Bypass Results` | Table: bypass id, blocked, bypassed, or not covered, command |
| `## Gaps` | Not covered bypasses and DEFERRED or DOCS-ONLY rules, stated plainly |

## Cleanup

Remove the disposable worktree: `git worktree remove --force <temp>`. Confirm `git worktree list` no longer shows it, and `git status` in the user's tree is unchanged from before.
