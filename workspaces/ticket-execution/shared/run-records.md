# Run records

A run is keyed by the Jira key. Each stage writes into `stages/0N-*/output/<KEY>/`. Later stages read earlier records. Earlier stages never read later ones. Records are run history, not templates (do not copy another key's records). Output folders are git-ignored.

| Stage | Folder `stages/.../output/<KEY>/` | Files | Holds |
|-------|-----------------------------------|-------|-------|
| 01 | `01-intake/` | `issue.json`, `ticket.md`, `attachments/`, `intake.md` | Raw item, the readable ticket, the files, the working summary |
| 02 | `02-research/` | `research.md` | Where the behavior lives, siblings, prior decisions, with paths |
| 03 | `03-plan/` | `plan.md` | Scope, files, branch, work tree, acceptance checklist, review URLs |
| 04 | `04-implement/` | `implement-record.md` | Branch, work tree path, base commit, files changed, plan deviations, lint |
| 05 | `05-verify/` | `verify-report.md`, `shots/`, `dev-server.json`, `dev-server.log` | One row per acceptance line with PASS, FAIL or NOT VERIFIED; the server the run started |
| 06 | `06-handoff/` | `handoff.md` | What you review, where, and on which server |
| 07 | `07-release/` | `release-record.md` | Commit, push, PR URL |

A change pass (`change <KEY>: ...`) rewrites 04, 05 and 06 for the key. The old files are replaced, and `implement-record.md` keeps a "Changes" list with one line per pass.

## How `status` works

List each `<KEY>` folder under `stages/01-intake/output/`. For each key, a stage is COMPLETE when its main file exists (`intake.md`, `research.md`, `plan.md`, `implement-record.md`, `verify-report.md`, `handoff.md`, `release-record.md`), otherwise PENDING. Show the waiting state in words:

- `plan.md` and no `implement-record.md`: "04 not started" (an interrupted run, not waiting on you).
- `handoff.md` newer than any `release-record.md`: "06 waiting for your review", followed by the URLs from `handoff.md` and whether the server still answers (`tools/dev_server.py status --app-root <app root>`).

```
Pipeline Status: ticket-execution

OND-7  rich image grid section
  [01-intake] -> [02-research] -> [03-plan] -> [04-implement] -> [05-verify] -> [06-handoff] -> [07-release]
   COMPLETE       COMPLETE         COMPLETE      COMPLETE          COMPLETE       COMPLETE        PENDING
  06 waiting for your review: http://localhost:3001/model/ora-05-raz-test/ (server answers)
```
