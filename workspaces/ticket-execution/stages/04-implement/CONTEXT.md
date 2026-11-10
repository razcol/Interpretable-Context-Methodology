# Stage 04: Implement

version: 1

Make the planned change on the planned branch and work tree. Nothing is staged, committed or pushed. Runs when this stage is assigned, including a change pass. The record's first line is `version: 1`.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 03 | `../03-plan/output/<KEY>/plan.md` | Full file, as written | What to build, where, including defaults |
| Stage 01 | `../01-intake/output/<KEY>/intake.md` | "Acceptance", "Images" | The lines to satisfy |
| Stage 01 | `../01-intake/output/<KEY>/attachments/` | Images the plan names | Visual target |
| Stage 02 | `../02-research/output/<KEY>/research.md` | "Per acceptance line" | Paths and sibling patterns |
| Work tree | `references/work-tree.md` | Full file | Branch and worktree commands, lint, record |
| Git | `../../shared/git-rules.md` | "Allowed per stage", "Never staged", "Your work comes first" | Limits |
| Repos | `../../targets/repos.md` | "Lint" | The lint command for this root |
| You | `change <KEY>: <text>` | The text | What to change in a change pass |
| Records | `../../shared/tools.md` | "Writing records" | How to write this stage's record when the chat is rooted in the app repo |

Do not read stage 05, 06 or 07 records, contexts or references. This stage's inputs are the rows above.

## Process

1. Read `plan.md` as written, including each default under "Questions". On a change pass, also read the change text in the assignment. Do not ask which word started the run.
2. Set up the branch and work tree as `plan.md` says, with the commands in `references/work-tree.md`. Write the branch and path into `implement-record.md` first.
3. Make the change file by file in the plan's order. Follow the repo's own patterns (the sibling and nearby files in `research.md`), not general habits.
4. In a change pass, change only what your text asks, on the same branch. Record the diff size against the base before the edit and after it (`git diff --stat origin/dev`). When the text says to simplify, reduce or remove, the after diff must be smaller, or the record explains why not. Name one smaller option you considered and rejected, with the reason. On a simplify, reduce or remove pass, read `git diff origin/dev` after the edit, which covers the whole branch and not only this pass. List each added item of these three kinds:
   - a new field in an `interface` or `type`
   - a new helper: a function, an arrow-function const, or a hook that does not exist on `origin/dev`
   - a display string that falls back to an error code, for example `ErrorMessage || ErrorCode`, `?? code`, or a code placed in rendered text.

   Remove each one, or say in one line why it stays.
5. Run lint on the changed files with the command in `targets/repos.md` "Lint" (`references/work-tree.md` "Lint"). Fix what the change caused. Do not look for another eslint or prettier config.
6. Finish `implement-record.md`. Return its path and each audit row. Do not open stage 05.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Plan | Every file changed is in `plan.md` "Files", or listed under "Deviations" with a reason |
| Nothing staged | `git diff --cached --name-only` is empty and no new commit exists on the branch |
| Your work | Files that were dirty before the run are unchanged |
| No records | No report, summary or plan markdown inside the root |
| Lint | No new lint errors in changed files. When lint was deferred to 05, the row reads `deferred`, never pass |
| Change | On a change pass, the record states the goal of the change text in one line and the diff size against the base before and after. When the text says to simplify, reduce or remove, the after diff is smaller, or the record explains why not. A simplify pass names one smaller option considered and rejected. On a simplify, reduce or remove pass, `added surface` lists every new interface field, new helper, and display string falling back to an error code in the branch diff. Each is marked `removed` or `kept: <reason>`, or the line reads `none` |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Code | The work tree in `plan.md` | Unstaged changes |
| Record | `output/<KEY>/implement-record.md` | See `references/work-tree.md` "Record" |
