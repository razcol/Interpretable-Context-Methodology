# Stage 02: Measure

Run the probes and produce one small, validated report for each.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../01-recon/output/project-profile.md` | "Run" and "Not Applicable Probes" sections | Repo path, sha, probes to skip |
| Routing | `../../playbooks/CONTEXT.md` | "What Loads" table, Probes column | Which probe folders to list |
| Shared | `../../shared/probe-report-schema.md` | Full file | Report shape, caps, drill-down rule |
| Shared | `../../shared/dispatch.md` | "Work Units", "Fallback", "With Subagents" | How to run units |
| Shared | `../../shared/scripts-reference.md` | "measure.mjs" and "probe-runner.mjs" | Script usage |
| Reference | `references/run-procedure.md` | Full file | Commands and confidence levels |

## Process

1. Read the Run section. Confirm the repo HEAD still equals the recorded sha. If it moved, stop.
2. List pending probes with `probe-runner.mjs list`.
3. Write the probes to skip, with reasons, to `output/skipped-probes.md`.
4. Run each remaining probe with `measure.mjs`, one unit of work each (in parallel if dispatch allows).
5. For each report, fill Interpretation and Unknowns, and set confidence and status. Open no other report.
6. Run `probe-runner.mjs validate`. Fix each failing report once. A second failure goes to the user.
7. Run the audit.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Every probe accounted for | Each listed probe has a valid report or a line in skipped-probes.md |
| Validator passes | `probe-runner.mjs validate` exits 0 |
| Fresh reports | Every report carries the sha from the profile |
| Size cap | No report is over 6000 characters |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Probe reports | `output/reports/<probe-id>.md` | Fixed schema from `probe-report-schema.md` |
| Evidence | `output/evidence/` | Tab-separated file lists and outlier lists |
| Skipped probes | `output/skipped-probes.md` | One line per skipped probe with a reason |
