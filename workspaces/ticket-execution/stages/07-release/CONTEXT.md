# Stage 07: Release

version: 1

After you approve: stage the reviewed files, commit with the key, push the branch, and give you the create-PR link against `dev`. Runs only on `approve <KEY>` (commit and push) or `commit <KEY>` (commit only).

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 06 | `../06-handoff/output/<KEY>/handoff.md` | "files", "dev artifacts left out", branch, work tree | What you reviewed |
| Stage 03 | `../03-plan/output/<KEY>/plan.md` | "Change" | Commit subject source |
| Steps | `references/release-steps.md` | Full file | Commands, record |
| Git | `../../shared/git-rules.md` | "Allowed per stage", "Never staged", "Commit and PR" | Limits, subject, PR URL |
| Repos | `../../targets/repos.md` | The root's row | Commit subject pattern, slug |

## Process

1. The record's first line is `version: 1`. The assignment says `approve` (commit and push) or `commit` (commit only). If it says neither, stop and name the two words.
2. Compare `git status` in the work tree with "files" in `handoff.md`. Files changed since the handoff that are not dev artifacts: list them and ask once whether they go in. Do not guess.
3. Stage exactly the reviewed files by path, commit, and on `approve` push, with the commands in `references/release-steps.md`. When `release-record.md` already shows a commit that was not pushed, `approve` only pushes.
4. Write `release-record.md` and reply with the commit, the push result and the PR link.
5. Leave the branch, the work tree and the dev server as they are. Say `stop <KEY>` stops the server.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 2 | Files changed after the handoff | Include them, or leave them out of the commit |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Exact | `git show --stat HEAD` lists the reviewed files and nothing else |
| Excluded | No file from "Never staged" in the commit |
| Subject | Follows the repo pattern and has the key |
| Push | On `approve`: `git status -sb` shows the branch tracking `origin/<branch>` with nothing ahead |
| No API | No Bitbucket or Jira API call was made |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Record | `output/<KEY>/release-record.md` | Commit hash and subject, files, push result, PR URL |
