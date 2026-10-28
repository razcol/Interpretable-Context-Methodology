# Rules Manifest Schema

The canonical shape of convention candidates and rules. `scripts/probe-runner.mjs validate-candidates` and `validate-rules` enforce it. The agent guide, the coverage matrix, and the lint configuration all derive from these blocks, so nothing is defined twice.

## Candidate Block

```
### C-001: Short title
- rule: One sentence, imperative. What is allowed or forbidden.
- dominant: The variant most files use.
- evidence: Report names and the numbers that matter.
- trend: stable | growing | shrinking | migration (new files differ from the majority)
- risk_if_wrong: What breaks or regresses if this rule is enforced and is wrong.
- corroboration: A second report with a different method that agrees, or "none".
- decision: pending | ratified | rejected | changed
- ratifier_note: Optional. Required when corroboration is "none" and the decision is ratified.
```

## Rule Block

```
### R-001: Short title
- status: READY | DEFERRED | DOCS-ONLY | DROPPED
- source: The candidate id, for example C-001
- rationale: Why the rule exists, one sentence.
- evidence: Report names and numbers.
- mechanism: The exact tool and setting, for example "eslint no-restricted-imports".
- ladder: 1 to 5. See shared/enforcement-ladder.md.
- dry_run_cmd: `command that counts violations without changing the repo`
- violations: Integer counted by running dry_run_cmd. "n/a" only for DOCS-ONLY.
- confidence: high | medium | low
- message: The text an agent sees when the rule fires. Includes the fix.
- decision: Required for DEFERRED (skip or cleanup-first). drop for DROPPED.
```

## Status Rules (checked by script)

| Status | Required |
|--------|----------|
| READY | `violations` is exactly 0. Ladder 1 to 4. |
| DEFERRED | `violations` is 1 or more, and `decision` is `skip` or `cleanup-first`. |
| DOCS-ONLY | Ladder 5. Nothing enforces it. |
| DROPPED | `decision` is `drop`. Kept for the record. |

A rule becomes READY only when a dry run returns 0. Nobody edits the number by hand.

## IDs

Ids are never reused. A dropped rule keeps its id. Ladder levels and statuses are the only closed vocabularies. Everything else is free text.
