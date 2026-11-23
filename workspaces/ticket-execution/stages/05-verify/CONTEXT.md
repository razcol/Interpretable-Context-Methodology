# Stage 05: Verify

version: 1

Check each acceptance line in the running app with a headless browser, and record PASS, FAIL or NOT VERIFIED. The dev server stays up for stage 06. The report's first line is `version: 1`.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 03 | `<runs>/<RUN>/03-plan/plan.md` | "Acceptance checklist", "Review URLs", "app root" | What to check, where, at which widths |
| Stage 04 | `<runs>/<RUN>/04-implement/implement-record.md` | Full file | Work tree, app root, files, lint state |
| Stage 01 | `<runs>/<RUN>/01-intake/attachments/` | Images the checklist names | What it should look like |
| Stage 03b | `<runs>/<RUN>/03b-baseline/baseline-record.md` | Full file (when present) | Baseline server, rows captured, widths, rows with no baseline |
| Stage 03b | `<runs>/<RUN>/03b-baseline/shots/` | `row<N>__<W>x<H>.png` (when present) | The Before shot each post-change screenshot is compared with |
| Steps | `references/verify-steps.md` | Full file | Server, browser commands, report shape |
| Tools | `../../shared/tools.md` | "run_claim.py", "dev_server.py", "Writing records" | The run's ports, start or reuse the server |
| Browser | `../../../../_core/skills/browser-cdp/SKILL.md` | "Which script to run", "Output contract", "Interaction steps" | Screenshots, annotations, measure, interact, capture |
| Repos | `<data-root>/workspaces/ticket-execution/repos.md` | "Test logins" (the root's row) | Sign-in steps file, secret key names, form submits |
| Repo rows | `../../shared/repo-rows.md` | "Test logins" | What Session and Form submits mean |

## Process

0. Sort the checklist before any server or browser. When "Form submits" is not `yes`, every row that sends a form is NOT VERIFIED with "submit not allowed", and it gets no browser. A row whose Check says `not checkable locally` is NOT VERIFIED with that text, and it gets no browser. When no row remains, write the report and return. Do not start the server or the browser for an empty remainder.
1. Start or reuse the dev server for the app root (`dev_server.py up` reuses the one `03b-baseline` started when it still runs on the same `<app>`) as `references/verify-steps.md` "Server" says. When lint was deferred, run it now. `eslint` reporting a JSON or config file (for example `He.json`) as ignored, or printing no output for it, is an expected no-op, not a failure (`references/verify-steps.md` "Lint").
2. Start the headless browser only when a row remains: the run's own profile and port (`references/verify-steps.md` "Run ports and browser"), or reuse it when it already runs.
3. For each remaining row, run its check on its URL at its widths in a fresh browser context. One `interact.js` call covers every remaining row on the same page and width. For a page behind a login, that context signs in only through the root's steps file (`references/verify-steps.md` "Pages behind a login"). Send a form only as "Form submits" says. For each UI-changing row, name the screenshot like its baseline (`row<N>__<W>x<H>`) and pass annotations on only the changed region (`references/verify-steps.md` "Annotated screenshots"). Open every screenshot and compare it with its `03b-baseline/shots/` match (when present) and with the ticket image. Console and page errors: on a page behind a login, take `consoleErrors` from that page's sign-in call, and do not run `capture.js` there. On a page with no login, run `capture.js` once per review URL. Errors never add a sign-in call. One exception: when a page's single sign-in call aborts on an overlay or selector error before it read any evidence, retry that page once (`references/verify-steps.md` "Pages behind a login") instead of leaving its rows NOT VERIFIED.
4. Write `verify-report.md`. Write only inside `<runs>/<RUN>/05-verify/`: no `/tmp/*.json` scratch files (keep temporary JSON in that folder or pass it inline), and no append to `log/browser-cdp/LOG.md` (stage 05 workers do not write skill logs).
5. On any FAIL caused by the change, keep the rows in the report. Do not edit code and do not open stage 04.
6. Stop the browser. Leave the dev server running. Return the report path and each audit row. Do not open stage 06.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Every row | Each checklist row has a result and evidence (a screenshot path, a number, or the HTML line) |
| Real check | A PASS comes from a fresh browser context (after the root's documented sign-in when the page needs one) or from the served HTML of the acceptance screen. Any other session, and lint, are never a PASS |
| Submits | No form was sent unless the root's "Form submits" is `yes`; each sent form has its response quoted |
| Images | Each row tied to a ticket image has its screenshot opened and compared, differences listed |
| Annotations | Every UI-changing row's post-change screenshot carries targeted, non-obstructing annotations with `applied: true` in the JSON `annotations` array (changed region only, no full-page box, no label covering key context), or `verify-report.md` gives the reason no selector applied. Each row with a baseline in `03b-baseline/shots/` notes the baseline comparison |
| Errors | New console or page errors on the review URLs are listed. On a page behind a login they come from the sign-in call's `consoleErrors`. A `capture.js` result for that page is not evidence |
| Clean | Browser stopped; dev server running; `git diff --cached` still empty |
| No idle browser | No browser was started when no row needed one |
| Sign-ins | The number of sign-in calls equals the number of distinct page and width pairs among the rows that needed a browser. A page whose first call aborted before reading evidence may add one retry; the report line reads `sign-ins: N (1 retry on <page>)` |
| Write scope | Every file written is under `<runs>/<RUN>/05-verify/`. No `/tmp/*.json`, no `log/browser-cdp/LOG.md` entry |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Report | `<runs>/<RUN>/05-verify/verify-report.md` | See `references/verify-steps.md` "Report" |
| Screenshots | `<runs>/<RUN>/05-verify/shots/` | PNG, annotated, named `row<N>__<W>x<H>.png` like `03b-baseline/shots/` |
| Server state | `<runs>/<RUN>/05-verify/dev-server.json`, `dev-server.log` | Written by `dev_server.py up`; stage 06 and `stop` read it |
