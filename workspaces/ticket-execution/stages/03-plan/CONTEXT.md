# Stage 03: Plan

version: 1

Write the plan stage 04 will follow: scope, files, branch, work tree, the acceptance checklist with how each line is checked, and the review URLs. Do not stop for review.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-intake/output/<KEY>/intake.md` | Full file | Acceptance, root, gaps |
| Stage 02 | `../02-research/output/<KEY>/research.md` | Full file | Paths, siblings, tree state |
| Shape | `references/plan-shape.md` | Full file | `plan.md` sections and rules |
| Repos | `../../targets/repos.md` | The root's row and "Rules" | Branch pattern, work tree, test route |
| Git | `../../shared/git-rules.md` | "The stop", "Your work comes first" | What the plan may promise |
| Records | `../../shared/tools.md` | "Writing records" | How to write this stage's record when the chat is rooted in the app repo |

## Process

1. The record's first line is `version: 1`. Pick the branch name and the work tree from the repo row, the tree state in `research.md`, and "Rules" in `targets/repos.md`. A re-run on an existing branch keeps that branch.
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
| Defaults | Every question states the default this run will take, or the section says none |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Plan | `output/<KEY>/plan.md` | See `references/plan-shape.md` |
