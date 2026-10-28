# Stage 04: Enforcement Design

Map each ratified rule to a mechanism, measure its violations, and sort rules into READY and DEFERRED.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../03-synthesize/output/conventions-candidates.md` | Candidates with decision ratified or changed | The rules to design |
| Earlier stage | `../01-recon/output/project-profile.md` | "Run" and "Tooling" sections | Repo path, sha, existing tools |
| Routing | `../../playbooks/CONTEXT.md` | "What Loads" table, Enforcement column | Which enforcement file to load |
| Shared | `../../shared/enforcement-ladder.md` | Full file | Choosing the mechanism |
| Shared | `../../shared/rules-manifest-schema.md` | "Rule Block" and "Status Rules" | Fields and status checks |
| Shared | `../../shared/deferral-policy.md` | Full file | READY versus DEFERRED |
| Shared | `../../shared/tamper-protection.md` | "Bypass Attempts" and "Protected Files" | The tamper plan |
| Shared | `../../shared/preferences.md` | "Allowed Dev Tools" | Which tools a rule may need |
| Reference | `references/plan-format.md` | Full file | Output shape, dry runs, follow-up pass |

## Process

1. If this is a follow-up pass, use "Follow-Up Pass" in `plan-format.md` and stop after it.
2. Read the ratified candidates. Ignore the others.
3. Write a rule block for each, using the strongest cheap mechanism and a message that names the fix.
4. Run every dry run (one unit each). Record the command, date, count, and up to 3 examples.
5. Set each status from its count and run `probe-runner.mjs validate-rules`.
6. Build the coverage matrix, the tamper plan, and a deferred entry for each DEFERRED rule.
7. Record the user's choice for each deferred rule. Validate again, then run the audit.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 6 | Coverage matrix, then each deferred rule with count, size, and approach | For each deferred rule: skip (default), cleanup-first, or drop |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Measured counts | Every rule except DOCS-ONLY has a dry-run command, date, and integer |
| READY means zero | `validate-rules` exits 0 |
| Deferred decided | Each DEFERRED rule has decision skip or cleanup-first |
| Tamper coverage | Every file a READY rule changes is in the protected list |
| Tools allowed | Every tool a READY rule needs is allowed in preferences |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Enforcement plan | `output/enforcement-plan.md` | Coverage matrix, rule blocks, tamper plan |
| Deferred rules | `output/deferred-rules.md` | One cleanup brief per DEFERRED rule |
