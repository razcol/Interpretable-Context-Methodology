# Handoff Formats

The two documents this stage writes. Both are generated from existing records. Nothing is invented.

## agent-guide.md

Written for an agent working in the hardened project. It is meant to be copied into the project as its agent instructions file.

| Heading | Content |
|---------|---------|
| `# Working in this project` | One paragraph: what the gates are and that passing them is required |
| `## Run the checks` | The check command, when to run it (before every commit and after every change), and that a failure must be fixed, not bypassed |
| `## Enforced rules` | One entry per READY and verified rule: id, the rule in one sentence, what to do instead, the message the gate shows |
| `## Never do` | Editing protected files, adding suppression comments, skipping hooks, adding dependencies outside the allow-list. Taken from the tamper plan. |
| `## Review manually` | DOCS-ONLY rules. No gate checks these. |
| `## Known gaps` | DEFERRED rules with their counts, and the plain statement that new code can still break them until they are enforced |
| `## Protected files` | The list from the change log |

Rules of writing:

- Each enforced entry uses the rule block's `rationale` and `message`. If they are weak, say so in the summary and do not rewrite the rule.
- Keep the guide under 120 lines. Agents read it on every task.
- Do not list a rule as enforced unless the verification report shows it caught.
- Use plain language. No tool jargon without one line of explanation.

## followup-plan.md

Tells the user what to do next for every rule that is not enforced.

| Heading | Content |
|---------|---------|
| `## Summary` | Counts: enforced, deferred, docs-only, dropped |
| `## Cleanup Order` | DEFERRED rules ordered by: `cleanup-first` decisions first, then size S, M, L |
| `## Per Rule` | For each: id, title, violations, size, approach, examples, test coverage, and the re-entry command `followup <rule-id>` |
| `## After Cleanup` | The follow-up pass steps in one short list |

The plan is advice. It does not perform any cleanup.

## Optional Copy Into The Project

Only if the user asks: copy `agent-guide.md` into the hardened branch as the project's agent instructions file, and commit it with a message of the form `harden: add agent guide`. Use the implement worktree. Then re-run the check command.
