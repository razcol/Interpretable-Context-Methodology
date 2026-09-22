# Stage 02: Clarify

Turn a raw skill request into unambiguous, testable requirements. New skills only -- always skipped in existing-skill mode.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../01-intake/output/intake-note.md` | Full file | The raw request to clarify |

## Process

1. Ask targeted questions to pin down exact scope: what inputs the skill should handle, what outputs it should produce, and what "working correctly" means.
2. Explicitly ask about hard constraints that would rule out an implementation path (no API credentials available, no server access, sandboxed environment only, etc.).
3. Present the clarified requirements back to the user for confirmation.
4. Write the clarified requirements doc.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 3 | Clarified scope, inputs/outputs, constraints, success criteria | Whether this accurately captures what they need before research begins |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Clarified requirements | `output/clarified-requirements.md` | Scope, inputs/outputs, constraints, success criteria |
