# Stage 05: Approval and Refine

Get explicit user sign-off on the tested draft before it gets published.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../04-draft-and-test/output/draft-skill/` | Full folder | The draft to review |
| Previous stage | `../04-draft-and-test/output/test-log.md` | Full file | Evidence of how it performed |

## Process

1. Present the tested draft and test results to the user.
2. User approves, or sends it back into `04-draft-and-test` with feedback for another revision pass.
3. Loop until approved.
4. Finalize the approved skill folder.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 1 | The draft SKILL.md and the test results | Approve as-is, or request specific revisions |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Approved skill | `output/approved-skill/` | Finalized SKILL.md + supporting scripts, ready to publish |
