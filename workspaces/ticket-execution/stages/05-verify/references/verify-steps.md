# Verify steps

`<ws>` is the workspace folder `../../../shared/tools.md` names (the brief gives its real path). `B` is `<checkout>/_core/skills/browser-cdp`, the browser-cdp folder of the same checkout (`<ws>/../../_core/skills/browser-cdp`). `R` is `<runs>/<KEY>/05-verify`. `<app>` is the app root from `implement-record.md`.

## Run ports and browser

Runs on other keys may be verifying at the same time, so this run uses only its own ports and browser profile. Get them once (each call returns the same port again):

```bash
python3 <ws>/../../_core/data-root/run_claim.py port --ws ticket-execution --key <KEY> --kind dev   # DEV
python3 <ws>/../../_core/data-root/run_claim.py port --ws ticket-execution --key <KEY> --kind cdp   # CDP
node $B/scripts/browser.js start --profile <p> --port <CDP>
```

`<p>` is the key in lowercase (`ond-123`); its port and `<p>` are the same in stage 06. Every browser call below carries `--profile <p>`, and `browser.js stop --profile <p>` stops it. Never use the default profile or port: another run's sign-in and tabs live there.

## Server

Skip this section when step 0 of the stage left no row that needs a browser. Write the report with those rows NOT VERIFIED and do not run `up`.

```bash
python3 <ws>/tools/dev_server.py up --app-root <app> --state $R/dev-server.json --port <DEV> --path <first review path>
```

Run it as a background shell command with no sandbox and full network, then wait for the JSON (up to 10 minutes on a fresh worktree). Use `port` from the JSON for every URL below (it differs from `<DEV>` when `up` reused this app root's server). On exit 6 or 7, read `tail` and the log, fix what the change broke, and run `up` again. An environment failure (AWS, database, VPN) is not the change: record it, mark the rows NOT VERIFIED, and return. Stage 06 reports it.

## Checks

| Check in plan | Command |
|---------------|---------|
| screenshot | `node $B/scripts/screenshot.js --profile <p> --url "http://localhost:<port><path>" --viewports <W>x<H>,... [--selector '<css>'] --name row<N> --out-dir $R/shots` |
| measure | `node $B/scripts/measure.js --profile <p> --url "http://localhost:<port><path>" --viewports ... [--selector '<css>'] --name row<N> --out-dir $R/shots --timeout 60000` (exit 11 is FAIL; `overflowPx` per width) |
| interact | `node $B/scripts/interact.js --profile <p> --url "http://localhost:<port><path>" --steps '[...]'` with `assert_*` steps for the expected result |
| view source | `curl -s "http://localhost:<port><path>"` and search the served HTML for the asked markup (heading level, `alt`, `loading="lazy"`, text present in the source) |
| errors | `node $B/scripts/capture.js --profile <p> --url "http://localhost:<port><path>" --out $R/capture-<N>.json` |

Use `--timeout 60000` on the first call to a page; the first compile takes about 30 seconds. Heights for widths: 1920x1080, 1440x900, 1100x800, 768x1024, 375x812.

A page that needs no login: run the check as a new visitor. An HTTP status is not the check.

A section not on the page (`ELEMENT_NOT_FOUND`) means the CMS page does not include it yet. The row is NOT VERIFIED with "not placed on <path>", not FAIL.

## Pages behind a login

Read the root's row in `<data-root>/workspaces/ticket-execution/repos.md` "Test logins". `L` is its steps file under `<data-root>/workspaces/ticket-execution/logins/`, and `S` is the secrets file that section names (`~/.config/ticket-execution/test-logins.env` by default). Do not open `S`. Each check is one call: a fresh context, the documented sign-in, then the row in the same tab.

```bash
node $B/scripts/interact.js --profile <p> --fresh-context --viewport <W>x<H> --timeout 60000 \
  --url "http://localhost:<port><login path>" --steps-file $L --secrets-file $S --out-dir $R/shots \
  --steps '[{"action":"goto","url":"http://localhost:<port><path>"}, <row steps>, {"action":"screenshot","name":"row<N>__<W>x<H>"}]'
```

- The sign-in takes about 35 seconds. One `interact.js` call per page and width covers all of that page's remaining rows. The number of sign-ins equals the number of distinct page and width pairs. A second sign-in for the same pair fails the Sign-ins audit row.
- PASS when that call shows the acceptance UI. A sign-in done any other way (values typed from a prompt, your own steps, `sessionStorage` written by hand) is NOT VERIFIED with "needs login".
- A root with no "Test logins" row, or a call that fails inside the steps file: NOT VERIFIED with "needs login" and the failed step. A captcha that blocks the sign-in is recorded as such. Do not look for a bypass in the code or the env.
- `screenshot.js`, `measure.js` and `capture.js` open new tabs without the session. On these pages, use the `screenshot` step and `consoleErrors` from `interact.js` instead.

## Form submits

A row whose Check says `submits` sends the form only when the root's "Form submits" in `<data-root>/workspaces/ticket-execution/repos.md` is `yes`. Otherwise the row is NOT VERIFIED with "submit not allowed on this backend" and the browser stays closed for that row. Do not fill the form.

When you submit, add `--responses '<request path or service name>'` and quote the field the row is about (for example `ErrorMessage`) next to the text on screen in Evidence. Do not write your own network listener.

## Report

`R/verify-report.md`:

```markdown
# <KEY> verify

version: 1

- server: http://localhost:<port> from <app> (<reused | started | not started>)
- lint: <result>
- result: <N PASS, N FAIL, N NOT VERIFIED>

| # | Line | Check | Result | Evidence |
|---|------|-------|--------|----------|
| 1 | <line> | screenshot 1440, 375 | PASS | `shots/row1__1440x900.png`, matches image-2026...png except <...> |

## Console and page errors
<New errors per URL, or none.>

## Not verified
<Each row with the reason and what you can do to check it. Or none.>
```
