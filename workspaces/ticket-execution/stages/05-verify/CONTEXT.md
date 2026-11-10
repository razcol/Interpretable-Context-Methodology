# Stage 05: Verify

version: 1

Check each acceptance line in the running app with a headless browser, and record PASS, FAIL or NOT VERIFIED. The dev server stays up for stage 06. The report's first line is `version: 1`.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 03 | `../03-plan/output/<KEY>/plan.md` | "Acceptance checklist", "Review URLs", "app root" | What to check, where, at which widths |
| Stage 04 | `../04-implement/output/<KEY>/implement-record.md` | Full file | Work tree, app root, files, lint state |
| Stage 01 | `../01-intake/output/<KEY>/attachments/` | Images the checklist names | What it should look like |
| Steps | `references/verify-steps.md` | Full file | Server, browser commands, report shape |
| Tools | `../../shared/tools.md` | "dev_server.py", "Writing records" | Start or reuse the server |
| Browser | `../../../../_core/skills/browser-cdp/SKILL.md` | "Which script to run", "Output contract", "Interaction steps" | Screenshots, measure, interact, capture |
| Repos | `../../targets/repos.md` | "Test logins" (the root's row) | Sign-in steps file, secret key names, form submits |

## Process

0. Sort the checklist before any server or browser. When "Form submits" is not `yes`, every row that sends a form is NOT VERIFIED with "submit not allowed", and it gets no browser. When no row remains, write the report and return. Do not start the server or the browser for an empty remainder.
1. Start or reuse the dev server for the app root as `references/verify-steps.md` "Server" says. When lint was deferred, run it now.
2. Start the headless browser (`browser.js start`, or reuse) only when a row remains.
3. For each remaining row, run its check on its URL at its widths in a fresh browser context. One `interact.js` call covers every remaining row on the same page and width. For a page behind a login, that context signs in only through the root's steps file (`references/verify-steps.md` "Pages behind a login"). Send a form only as "Form submits" says. Open every screenshot and compare it with the ticket image. Console and page errors: on a page behind a login, take `consoleErrors` from that page's sign-in call, and do not run `capture.js` there. On a page with no login, run `capture.js` once per review URL. Errors never add a sign-in call.
4. Write `verify-report.md`.
5. On any FAIL caused by the change, keep the rows in the report. Do not edit code and do not open stage 04.
6. Stop the browser. Leave the dev server running. Return the report path and each audit row. Do not open stage 06.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Every row | Each checklist row has a result and evidence (a screenshot path, a number, or the HTML line) |
| Real check | A PASS comes from a fresh browser context (after the root's documented sign-in when the page needs one) or from the served HTML of the acceptance screen. Any other session, and lint, are never a PASS |
| Submits | No form was sent unless the root's "Form submits" is `yes`; each sent form has its response quoted |
| Images | Each row tied to a ticket image has its screenshot opened and compared, differences listed |
| Errors | New console or page errors on the review URLs are listed. On a page behind a login they come from the sign-in call's `consoleErrors`. A `capture.js` result for that page is not evidence |
| Clean | Browser stopped; dev server running; `git diff --cached` still empty |
| No idle browser | No browser was started when no row needed one |
| Sign-ins | The number of sign-in calls equals the number of distinct page and width pairs among the rows that needed a browser |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Report | `output/<KEY>/verify-report.md` | See `references/verify-steps.md` "Report" |
| Screenshots | `output/<KEY>/shots/` | PNG |
| Server state | `output/<KEY>/dev-server.json`, `dev-server.log` | Written by `dev_server.py up`; stage 06 and `stop <KEY>` read it |
