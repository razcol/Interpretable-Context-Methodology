# Run records

A run is keyed by the Jira key. Each stage writes into `<runs>/<KEY>/0N-*/` (`<runs>` is `<data-root>/workspaces/ticket-execution/runs`; CLAUDE.md). Later stages read earlier records. Earlier stages never read later ones. Records are run history, not templates (do not copy another key's records). Run folders are in the data root, never in this repo. Records written before run folders moved to the data root name paths as `stages/0N-*/output/<KEY>/...`. Read such a path as `<runs>/<KEY>/0N-*/...`; never recreate it in the repo.

| Stage | Folder `<runs>/<KEY>/.../` | Files | Holds |
|-------|-----------------------------------|-------|-------|
| 01 | `01-intake/` | `issue.json`, `ticket.md`, `attachments/`, `intake.md` | Raw item, the readable ticket, the files, the working summary |
| 02 | `02-research/` | `research.md` | Where the behavior lives, siblings, prior decisions, with paths |
| 03 | `03-plan/` | `plan.md` | Scope, files, branch, work tree, acceptance checklist, review URLs |
| 03b | `03b-baseline/` | `baseline-record.md`, `shots/`, `dev-server.json`, `dev-server.log` | Clean pre-edit screenshots (`row<N>__<W>x<H>.png`) from `origin/<base>`, or `status: skipped (<reason>)`; the server it started |
| 04 | `04-implement/` | `implement-record.md` | Branch, work tree path, base commit, files changed, plan deviations, lint |
| 05 | `05-verify/` | `verify-report.md`, `shots/`, `dev-server.json`, `dev-server.log` | One row per acceptance line with PASS, FAIL or NOT VERIFIED; the server the run started |
| 06 | `06-handoff/` | `handoff.md` | What you review, where, and on which server |
| 07 | `07-release/` | `release-record.md` | Commit, push, PR URL |

A change pass (`change <KEY>: ...`) rewrites 04, 05 and 06 for the key. The old files are replaced, and `implement-record.md` keeps a "Changes" list with one line per pass. A change pass never touches `03b-baseline/`: baselines persist across retries and change passes, and stage 03b does not run again while `baseline-record.md` exists.

## How `status` works

List each `<KEY>` folder under `<runs>/` that has `01-intake/`. For each key, a stage is COMPLETE when its main file exists (`intake.md`, `research.md`, `plan.md`, `baseline-record.md`, `implement-record.md`, `verify-report.md`, `handoff.md`, `release-record.md`), otherwise PENDING. Show the waiting state in words:

- `plan.md` and no `implement-record.md`: "04 not started" (an interrupted run, not waiting on you). `baseline-record.md` is optional for this line: a `skipped` baseline counts as COMPLETE, and a missing one on a key whose run came before stage 03b is not an error.
- `handoff.md` newer than any `release-record.md`: "06 waiting for your review", followed by the URLs from `handoff.md` and whether the server still answers (`tools/dev_server.py status --app-root <app root>`).

Then the runs that hold a claim now: `python3 ../../_core/data-root/run_claim.py list --ws ticket-execution` from this workspace folder. Each `live` run is "running since <startedAt> (pid <pid>, checkout <checkout>)" with its ports and work tree; a `stale` one is "stopped without release; the next `start` continues it". A run folder may hold `claim.lock`: it is the claim, not a record, and the data repo never commits it.

```
Pipeline Status: ticket-execution

ABC-7  rich image grid section
  [01-intake] -> [02-research] -> [03-plan] -> [03b-baseline] -> [04-implement] -> [05-verify] -> [06-handoff] -> [07-release]
   COMPLETE       COMPLETE         COMPLETE      COMPLETE         COMPLETE          COMPLETE       COMPLETE        PENDING
  06 waiting for your review: http://localhost:3001/<test route>/ (server answers)

Running now:
  XYZ-9  running since 2026-11-19T10:02 (pid 4242), dev 3002, browser 9341, work tree <root>/.worktrees/XYZ-9
```
