# Stage 05: Implement

Build the READY rules on a new branch in the target repo, without touching application code.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../04-enforcement-design/output/enforcement-plan.md` | "Run", READY rule blocks, "Tamper Plan", "Tooling Needed" | What to build |
| Earlier stage | `../01-recon/output/project-profile.md` | "Run" and "Tooling" sections | Base sha, package manager, build and test scripts |
| Shared | `../../shared/implementation-rules.md` | Full file | Worktree, branch, paths, fixtures, change log |
| Routing | `../../playbooks/CONTEXT.md` | "What Loads" table, Implementation column | Which implementation file to load |
| Shared | `../../shared/preferences.md` | "Branch Prefix", "Check Command", "Allowed Dev Tools" | Names and permitted installs |
| Shared | `../../shared/tamper-protection.md` | "Protected Files" and "Integrity Check" | The integrity step |

## Process

1. Confirm the repo HEAD equals the sha in the plan's Run section. If it moved, stop.
2. Re-run every READY rule's dry run. A non-zero count stops the stage and returns to Stage 04.
3. Create the worktree and the branch as `implementation-rules.md` describes.
4. Install only the allowed dev tools, at exact versions, using the lockfile.
5. For each READY rule: implement it, add its two fixtures and the fixture test, and commit.
6. Build the check command with the protected-file integrity step, and add one CI step that calls it.
7. Verify: check command, build, tests, and the changed-path list.
8. Write the change log. Do not push, open a pull request, or merge.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Gates pass | The check command exits 0 in the worktree |
| App still builds | The build script exits 0, and tests pass if the project has them |
| No application changes | Every changed path is on the allowed list |
| Fixtures work | Each rule has a should-fail fixture that fails and a should-pass fixture that passes |
| Deferred absent | No DEFERRED or DOCS-ONLY rule id appears in any config or rule file |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Hardened branch | The target repo, in a separate worktree | Commits as described in `implementation-rules.md` |
| Change log | `output/change-log.md` | Sections listed under "Change Log Format" in `implementation-rules.md` |
