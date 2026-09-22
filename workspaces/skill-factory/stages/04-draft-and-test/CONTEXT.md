# Stage 04: Draft and Test

Build a working draft and validate it against real usage. This is where new-skill and existing-skill maintenance paths converge.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../03-research/output/candidate-approaches.md` | Full file | Candidates to draft and test (new mode, or existing mode exploring a new approach) |
| Previous stage | `../01-intake/output/intake-note.md` | Resolved skill folder path | The current skill to re-test directly (existing mode, standard maintenance) |
| Shared | `../../shared/authoring-conventions.md` | Full file | How to write the SKILL.md draft |
| Shared | `../../shared/test-log-format.md` | Full file | Consistent shape for the test trace |
| User | (conversation) | Real day-to-day use case | What the skill is tested against |

## Process

1. For each viable candidate approach, build a lightweight draft SKILL.md (+ supporting scripts).
2. Get a real day-to-day use case from the user, or suggest one if they don't have one ready.
3. Run the draft against the use case. Log steps taken, decisions made, and reasoning as the trace.
4. For existing-mode maintenance: run the current skill as-is against a fresh real-world case; look for gaps or improvement opportunities even if it technically passes.
5. Compare results across candidates (new mode only). Select the winner respecting user constraints -- a workable approach the user can actually run beats a cleaner one they cannot.
6. Keep more than one approach only if they genuinely serve different contexts. This stays an internal agent decision, not something the user has to manage.
7. Revise the draft or existing skill in place based on findings.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 5 | Test results per candidate, and the selected approach with reasoning | Whether the selection is right, or a different candidate/constraint should be reconsidered |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Real usage tested | The draft/skill was run against an actual day-to-day use case, not a hypothetical one |
| Outcome matches expectation | The test log states a concrete outcome and how it compares to what was expected |
| Constraint compliance | The selected approach does not violate any hard constraint identified in clarification |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Test run log | `output/test-log.md` | Ephemeral trace per attempt: steps, decisions, reasoning, outcome. Not carried downstream. |
| Selected draft | `output/draft-skill/` | Working SKILL.md + supporting scripts for the selected/updated approach |
