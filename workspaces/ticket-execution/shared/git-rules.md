# Git rules

What may happen to a repo, and when. This file is the only home for these rules. Stages point here.

## The stop

After stage 06 the run stops for your review of the running app. Only `approve <KEY>`, `commit <KEY>`, or `change <KEY>: ...` crosses it. "Prepare", "review", "assist", "looks good", and "continue" do not. Stages 01 to 05 do not stop for review. A question in `plan.md` names a default, and the run takes that default. The branch and the edits happen in stage 04, before you look. Nothing is staged, committed, or pushed before the stop.

## Allowed per stage

| Stage | Allowed | Never |
|-------|---------|-------|
| 01 to 03 | Read files, `git log`, `git show`, `git diff`, `git fetch` | Any edit under the root, branch, checkout, worktree |
| 04 | `git fetch`, create the branch and work tree named in `plan.md`, edit files | `git add`, `stash`, `commit`, `amend`, `reset`, `rebase`, `push`, PR API calls |
| 05, 06 | Run lint, the dev server and the browser | Same as 04, and no code edits (a fix is a new stage 04 assignment) |
| 07 | `git add` of the reviewed files, `commit`, `push -u origin <branch>` | `--force`, `amend`, PR API calls, Jira writes |

Force-push and amend run only when you type those words for that key. Amend means the file is gone from the commit as if it was never there.

## Never staged

- Workspace records: anything under this workspace, report or summary markdown, `field-report.md`.
- Dev server output: `code/prisma/schema.prisma` unless `plan.md` lists it, `code/AGENTS.md` or `CLAUDE.md` blocks between `nextjs-agent-rules` markers, `code/.env*`, `.next/`, logs.
- Files you changed by hand that the handoff did not list. Stage 07 asks once about those.
- Unused assets the code does not import.

## Your work comes first

- Never stash, reset, checkout over or delete changes that were in the tree before the run. If the root is dirty, the plan uses a worktree.
- Never delete a branch or a worktree. Stage 07 leaves both in place.
- A bundle of tickets is one branch only when `plan.md` says so, and then one commit per key.

## Commit and PR

- Subject: the repo's pattern in `targets/repos.md`, one line, what changed for the user.
- Body: none, unless the plan lists follow-ups.
- PR URL: `https://bitbucket.org/colwebteam/<slug>/pull-requests/new?source=<branch>&dest=dev`. You open the PR. The agent never calls the Bitbucket API and never reads a credential file.
