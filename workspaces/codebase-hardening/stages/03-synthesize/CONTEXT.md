# Stage 03: Synthesize

Turn probe reports into convention candidates, and get the ratifier's decision on each.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../02-measure/output/reports/` | Every report. Not the evidence folder. | The facts to synthesize |
| Previous stage | `../02-measure/output/skipped-probes.md` | Full file | Known blind spots |
| Earlier stage | `../01-recon/output/project-profile.md` | "Stack" and "Tooling" sections | Cross-check dependency and config facts |
| Shared | `../../shared/rules-manifest-schema.md` | "Candidate Block" | Fields of a candidate |
| Shared | `../../shared/preferences.md` | "Ratifier" | Who decides |
| Reference | `references/candidates-format.md` | Full file | Method, corroboration, presentation |

## Process

1. Read all reports. Open evidence or source files only through a drill-down task.
2. Group reports by dimension and name the dominant variant of each.
3. Read each Trend. Where new code diverges from the majority, record a migration and follow the new code.
4. Find a second, independent report for every candidate you would enforce.
5. Write the candidates as blocks with decision `pending`.
6. Apply the ratifier's decisions. Copy notes from other reviewers into `ratifier_note`.
7. Run `probe-runner.mjs validate-candidates --final`, then the audit.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 5 | Table of id, rule, dominant, trend, corroboration, and risk | Ratify, reject, or reword each candidate. Paste notes from other reviewers. |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Evidence cited | Every candidate names at least one report |
| Numbers match | Each number in a candidate equals the number in its cited report |
| Decisions final | `validate-candidates --final` exits 0 |
| Migration honored | A candidate marked migration follows the direction of the newest files |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Convention candidates | `output/conventions-candidates.md` | Candidate blocks with final decisions |
