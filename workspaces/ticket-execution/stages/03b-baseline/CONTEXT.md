# Stage 03b: Baseline

version: 1

Capture clean "before" screenshots of the pages the plan will check, on a branch or work tree cut from `origin/<base>` with none of this run's edits, so stage 05 can compare them with the changed pages. Nothing is edited, staged, committed or pushed, and no code is stashed, switched back or reverted to get a baseline. Runs after stage 03 and before stage 04. The record's first line is `version: 1`.

## When it runs

- Runs on `start` and on `plan`, after 03 and before 04.
- Never runs on `change`, `implement` or `approve`/`commit`.
- Never runs when `<runs>/<RUN>/03b-baseline/baseline-record.md` already exists: baselines persist across retries and change passes. A `plan` that replans keeps the existing baselines. Delete the folder by hand to recapture.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 03 | `<runs>/<RUN>/03-plan/plan.md` | "Acceptance checklist", "Review URLs", "base", "branch", "work tree", "app root" | Which rows are UI-checkable, their URLs and widths, where to create the branch |
| Stage 01 | `<runs>/<RUN>/01-intake/intake.md` | Repo root, base | Root and `<base>` |
| Steps | `references/baseline-steps.md` | Full file | Skip checks, claim, server, browser, captures, record shape |
| Work tree | `../04-implement/references/work-tree.md` | "Claim", "Branch in the main tree", "Worktree" | The same branch and worktree commands stage 04 uses |
| Tools | `../../shared/tools.md` | "run_claim.py", "dev_server.py", "Writing records" | The run's ports, start the server, write the record |
| Browser | `../../../../_core/skills/browser-cdp/SKILL.md` | "Which script to run", "Output contract", "Interaction steps" | Screenshots and the sign-in call |
| Verify | `../05-verify/references/verify-steps.md` | "Run ports and browser", "Pages behind a login" | Same ports, profile, sign-in call and screenshot names as stage 05 |
| Repos | `<data-root>/workspaces/ticket-execution/repos.md` | "Test logins" (the root's row) | Sign-in steps file, secret key names, form submits |
| Repo rows | `../../shared/repo-rows.md` | "Test logins" | What Session and Form submits mean |
| Git | `../../shared/git-rules.md` | "Allowed per stage", "Your work comes first" | Limits |

Do not read stage 05, 06 or 07 records. The two files named under Verify are references for commands, not records.

## Process

0. Skip checks, before any claim, server or browser. Write `baseline-record.md` with `status: skipped (<reason>)`, start nothing and return when any of these holds:
   - `plan.md` has no UI-checkable row: no screenshot, measure or interact row on a known URL.
   - Every UI-checkable row sends a form and the root's "Form submits" is `no`.
   - The branch already has commits or edits ahead of `origin/<base>` (an existing, modified branch): its pages are no longer clean, so there is nothing to baseline.
1. Claim the work tree and branch for this run, then create or switch to a clean branch or work tree from `origin/<base>` as `plan.md` says, with the commands in `../04-implement/references/work-tree.md` ("Claim" first). Do not stash, do not switch a modified branch back, do not revert anything. Stage 04 reuses this branch and path.
2. Start the dev server for the app root with `dev_server.py up` on the run's dev port (`run_claim.py port --key <RUN> --kind dev`), state file `<runs>/<RUN>/03b-baseline/dev-server.json`.
3. Start the headless browser on the run's CDP port (`run_claim.py port --key <RUN> --kind cdp`) with the profile `<run id lowercase>`.
4. Capture each UI-checkable row at its widths into `<runs>/<RUN>/03b-baseline/shots/row<N>__<W>x<H>.png` (the names stage 05 uses). On a page behind a login, one sign-in `interact.js` call per page and width covers all of that page's rows. A row that cannot be captured (section not placed, sign-in fails, no check) is listed with the reason and no file.
5. Stop the browser. Leave the dev server running: stage 05 reuses it on the same app root.
6. Write `baseline-record.md` as `references/baseline-steps.md` "Record" says. Write only inside `<runs>/<RUN>/03b-baseline/`: no `/tmp/*.json` scratch files (keep temporary JSON in that folder or pass it inline), and no append to `log/browser-cdp/LOG.md` (stage workers do not write skill logs). Return the record path and each audit row. Do not open stage 04.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Skip | When skipped, the record says `status: skipped (<reason>)` and names which step 0 check fired. No claim, server or browser was started |
| Clean base | The branch or work tree was cut from `origin/<base>` and `git diff origin/<base>` of the app root is empty at capture time. No stash, branch switch back or revert was used |
| Shots | Each captured row has `shots/row<N>__<W>x<H>.png` for every width it names, or is listed under "Not captured" with a reason |
| Sign-ins | The number of sign-in calls equals the number of distinct page and width pairs among the captured rows on login pages. A page whose first call aborted before any screenshot may add one retry; the record line reads `sign-ins: N (1 retry on <page>)` |
| Clean | Browser stopped; dev server running (unless skipped); `git diff --cached` still empty; no file edited in the app root |
| Write scope | Every file written is under `<runs>/<RUN>/03b-baseline/`. No `/tmp/*.json`, no `log/browser-cdp/LOG.md` entry |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Record | `<runs>/<RUN>/03b-baseline/baseline-record.md` | See `references/baseline-steps.md` "Record" |
| Screenshots | `<runs>/<RUN>/03b-baseline/shots/` | PNG, `row<N>__<W>x<H>.png` |
| Server state | `<runs>/<RUN>/03b-baseline/dev-server.json`, `dev-server.log` | Written by `dev_server.py up`; stage 05 and `stop` read it |
| Branch and work tree | The work tree in `plan.md` | Created from `origin/<base>`, no edits; stage 04 reuses it |
