# Stage 03: Plan

version: 1

Write the plan stage 04 will follow: scope, files, branch, work tree, the acceptance checklist with how each line is checked, and the review URLs. Do not stop for review.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `<runs>/<KEY>/01-intake/intake.md` | Full file | Acceptance, root, gaps |
| Stage 02 | `<runs>/<KEY>/02-research/research.md` | Full file | Paths, siblings, tree state |
| Shape | `references/plan-shape.md` | Full file | `plan.md` sections and rules |
| Repos | `<data-root>/workspaces/ticket-execution/repos.md` | The root's row, its "Notes" and "Test logins" | Branch pattern, work tree, test route |
| Repo rows | `../../shared/repo-rows.md` | "Columns", "Rules" | How to read the row |
| Git | `../../shared/git-rules.md` | "The stop", "Your work comes first" | What the plan may promise |
| Records | `../../shared/tools.md` | "Writing records" | How to write this stage's record when the chat is rooted in the app repo |

## Process

1. The record's first line is `version: 1`. Pick the branch name and the work tree from the repo row, the tree state in `research.md`, and "Rules" in `../../shared/repo-rows.md`. A re-run on an existing branch keeps that branch.
2. Write `plan.md` as `references/plan-shape.md` says. Only what the acceptance lines need. Every question includes the default this run will take.
3. Run the audit. Fix and rewrite until it passes.
4. Return the path to `plan.md` and each audit row. Do not create the branch. Do not open stage 04. Do not wait for an edit.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Every line | Each acceptance line from `intake.md` is in the checklist, or under "Not doing" with a reason |
| Checkable | Each checklist row names a check method and a URL with widths, or says "not checkable locally" and why |
| Files | Every file to change is a real path, or marked `new` |
| Branch | Name follows the repo pattern and includes the key |
| No edits | `git status` of the root is the same as in `research.md` |
| Small | No file or change that no checklist row needs |
| WordPress | Every WordPress name in "Change", "Files", "Risks", "Not doing", "Questions" or the checklist matches a live block in `research.md`. "create", "missing" or "does not exist" only for a name under `absent` on `ok: true` for the run's root. A new `.gql` selection only for a name under `present` on that root. A name under "Unconfirmed live", or with no live block, appears only as unconfirmed, and its checklist row says `not checkable locally: live schema unconfirmed for <name> (<code>)` |
| Defaults | Every question states the default this run will take, or the section says none |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Plan | `<runs>/<KEY>/03-plan/plan.md` | See `references/plan-shape.md` |
