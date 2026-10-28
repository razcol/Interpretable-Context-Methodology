# Deferral Policy

A new rule must never break a project that cannot afford to break. Rules with existing violations wait. Rules without them go in now.

## Classification

Each rule's dry run returns a violation count. The count is measured by a command, never estimated.

| Count | Status | Action |
|-------|--------|--------|
| 0 | READY | Implement now. The rule cannot affect existing code. |
| 1 or more | DEFERRED | Do not implement. Write a cleanup brief. Ask the user what to do. |
| Not checkable | DOCS-ONLY | Record in the agent guide. Nothing enforces it. |

## The Question For Each Deferred Rule

| Choice | Meaning |
|--------|---------|
| `skip` (default) | Leave the rule out for now. The follow-up plan lists it. |
| `cleanup-first` | The user wants to clean up soon. The follow-up plan puts it first. |
| `drop` | Reject the rule. It is kept in the record as DROPPED. |

If the user does not answer, the choice is `skip`. Never implement a DEFERRED rule to be helpful.

## Cleanup Brief

For each deferred rule the plan records:

- The violation count and the top directories by count
- Up to 3 example `path:line` pointers
- A size: S for 1 to 10, M for 11 to 50, L for more than 50
- A suggested approach: automatic (a codemod or an autofix exists) or manual
- Whether tests cover the affected code, taken from the recon profile

## Scope

This workspace plans the cleanup and never performs it. It does not rewrite existing application code. The user, or an agent in a normal session, does the cleanup.

## Follow-Up Pass

After the cleanup, the user starts a follow-up pass for that rule. The enforcement design stage re-runs only that rule's dry run. If it returns 0, the rule becomes READY and goes through implement, verify, and handoff for that rule alone. If it does not return 0, it stays DEFERRED with the new count.

## Visibility

The coverage matrix and the agent guide show every DEFERRED rule with its count. Until a rule is enforced, an agent can still write that anti-pattern in new code. The guide says so.
