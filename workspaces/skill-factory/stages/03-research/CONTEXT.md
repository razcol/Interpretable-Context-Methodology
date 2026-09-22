# Stage 03: Research

Explore viable implementation approaches for the skill before committing to one. Skipped for existing-skill maintenance unless the request is specifically to try a different approach.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../02-clarify/output/clarified-requirements.md` | Full file | Scope and constraints to research against (new mode) |
| Previous stage | `../01-intake/output/intake-note.md` | Resolved skill folder path | Current implementation to reconsider (existing mode, approach-change requests only) |
| Shared | `../../shared/authoring-conventions.md` | Full file | Keeps research grounded in what's actually implementable as a skill |
| Shared | `../../shared/preferences.md` | "Research Depth" | How thoroughly to compare candidate approaches before drafting |

## Process

1. Research viable implementation paths for the end goal (CLI tool, REST API, existing library, browser automation, etc.).
2. Note tradeoffs for each: cleanliness/efficiency vs. what the user's stated constraints actually permit.
3. Rule out paths that conflict with hard constraints identified during clarification. Note why.
4. Do not pick a winner yet -- selection happens after real-usage testing in Stage 04.
5. Write the candidate approaches doc.

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Candidate approaches | `output/candidate-approaches.md` | List of viable paths with tradeoffs, and ruled-out paths with reasons |
