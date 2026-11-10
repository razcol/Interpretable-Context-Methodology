# Ticket Execution

One Jira ticket becomes reviewed, running work in its local repo, then a pushed branch and a PR link once you approve. Triggers are in `CLAUDE.md`.

## Task Routing

| Task Type | Go To | Description |
|-----------|-------|-------------|
| Read a ticket | `stages/01-intake/CONTEXT.md` | Ticket, images, comments into files; resolve the repo |
| Research | `stages/02-research/CONTEXT.md` | Where it lives, siblings, earlier decisions |
| Plan | `stages/03-plan/CONTEXT.md` | Checklist, files, branch, review URLs, defaults; no stop |
| Implement or change | `stages/04-implement/CONTEXT.md` | Branch or worktree, the change, lint |
| Check it | `stages/05-verify/CONTEXT.md` | Browser checks per checklist row |
| Hand it over | `stages/06-handoff/CONTEXT.md` | Running app, URLs, diff summary; stop |
| Release | `stages/07-release/CONTEXT.md` | Commit, push, PR link after approval |

## Shared Resources

| Resource | Location | Contains |
|----------|----------|----------|
| Repos | `targets/repos.md` | Key to root, branch and commit patterns, work tree, test routes |
| Git rules | `shared/git-rules.md` | The stop, what each stage may do, never staged, PR URL |
| Run records | `shared/run-records.md` | Per-key folders, files per stage, `status` |
| Tools | `shared/tools.md` | `intake.py`, `dev_server.py`, `review_urls.py`, `write_record.py` commands and exit codes |
| Jira | `../../_core/skills/jira-research/SKILL.md` | ACLI install, sign-in, REST fallback |
| Browser | `../../_core/skills/browser-cdp/SKILL.md` | Screenshots, measure, interact, capture |
