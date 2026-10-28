# Enforcement Plan Format

The shape of this stage's two outputs, and how a follow-up pass works. Rule block fields are defined in `../../../shared/rules-manifest-schema.md`, section "Rule Block".

## enforcement-plan.md

Headings, in order:

| Heading | Content |
|---------|---------|
| `## Run` | Target repo path, sha the dry runs used, date, Primary Stack |
| `## Coverage Matrix` | Table: rule id, title, ladder, status, violations |
| `## Rules` | One rule block per rule, all statuses included |
| `## Tamper Plan` | Which bypasses from `../../../shared/tamper-protection.md` apply, the protected file list, the integrity check |
| `## Tooling Needed` | Dev dependencies the READY rules need, checked against Allowed Dev Tools in preferences |

Rules needing a tool that is not allowed stay un-implementable. Mark them DEFERRED with the reason "tool not allowed", violations counted anyway, and tell the user.

## deferred-rules.md

One entry per DEFERRED rule:

| Field | Content |
|-------|---------|
| Rule id and title | From the rule block |
| Violations | The measured count |
| Top directories | Up to 5 directories by count |
| Examples | Up to 3 `path:line` pointers |
| Size | S for 1 to 10, M for 11 to 50, L for more than 50 |
| Approach | `automatic` if a codemod or autofix exists, else `manual`, with the tool named |
| Test coverage | Whether tests cover the affected code, from the project profile |
| Decision | `skip` (default), `cleanup-first`, or `drop` |

## Dry Run Rules

1. Dry runs never write into the target repo. Temporary configs live in a system temp folder.
2. Record the exact command, the date, and the integer it returned in the rule block.
3. A rule that cannot be dry-run has unknown violations. Unknown is not zero. Ask the user.
4. Dry-run techniques per mechanism are in the playbook's enforcement file.

## Classification

Set each rule's status from its measured count using `../../../shared/deferral-policy.md`. Then run:

```
node ../../scripts/probe-runner.mjs validate-rules output/enforcement-plan.md
```

It must exit 0 before the checkpoint.

## Checkpoint Presentation

Show the coverage matrix. For each DEFERRED rule, show the count, size, and approach, and ask: skip (default), cleanup-first, or drop. Record the answer in the rule's `decision` field. A dropped rule becomes status DROPPED.

## Follow-Up Pass

Entered when the user says a deferred rule was cleaned up.

1. Read the rule's block and its deferred entry. Confirm the repo HEAD and record the new sha.
2. Re-run only that rule's dry run.
3. If the count is 0, set status READY, violations 0, and remove the deferred entry. Validate the rules file.
4. If not 0, update the count and examples and stop. Tell the user what remains.
5. Produce a plan containing only that rule for the implement stage. Keep the full earlier plan in place.
