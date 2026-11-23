# Baseline steps

`<ws>` is the workspace folder `../../../shared/tools.md` names (the brief gives its real path). `B` is `<checkout>/_core/skills/browser-cdp`, the browser-cdp folder of the same checkout (`<ws>/../../_core/skills/browser-cdp`). `R` is `<runs>/<KEY>/03b-baseline`. `<root>`, `<branch>`, `<path>`, `<base>` and `<app>` (the app root, `<work tree>/code`) come from `plan.md`. `<p>` is the key in lowercase (`ond-123`).

## Write scope

Everything this stage writes in the data root goes under `R`. Do not write `/tmp/*.json` scratch files: pass JSON inline (`--steps '[...]'`) or keep a temporary file inside `R`. Stage 03b workers do not append to `log/browser-cdp/LOG.md` or any other skill log; the orchestrator owns logs. The only other writes are the branch and worktree that `../../04-implement/references/work-tree.md` creates.

## Skip checks

Run these before any claim, server or browser, in this order. The first that holds is the reason.

| Check | Reason text |
|-------|-------------|
| `plan.md` "Acceptance checklist" has no row whose check is screenshot, measure or interact on a known URL (every row is `view source`, `not checkable locally`, or has no URL) | `no UI-checkable rows` |
| Every UI-checkable row sends a form and the root's "Form submits" in `<data-root>/workspaces/ticket-execution/repos.md` is `no` | `form submits: no` |
| `git -C <worktree or root> rev-list --count origin/<base>..<branch>` is above 0, or `git status --short` of the app root lists edits, for a branch that already exists | `existing modified branch` |

For the third check, use the branch from `plan.md` when it exists (`git -C <root> rev-parse --verify --quiet <branch>`). A branch or worktree that does not exist yet, or one that sits at `origin/<base>` with a clean tree, passes. Run `git -C <root> fetch origin` first (permission `all`).

When one holds, write the skipped record (see "Record") and return. No claim, no server, no browser.

## Claim, branch and worktree

Follow `../../04-implement/references/work-tree.md`: "Claim" first (`run_claim.py target ... --path <work tree> --root <root> --branch <branch>`), then "Branch in the main tree" or "Worktree", creating `<branch>` from `origin/<base>`. A work tree already on `<branch>` at `origin/<base>` with a clean tree is reused. Create nothing else.

Then confirm the baseline is clean, and put the result in the record:

```bash
git -C <work tree> rev-parse HEAD origin/<base>     # same hash
git -C <work tree> status --short                    # empty
```

When either differs, do not capture: this is not a baseline. Do not stash, reset, switch back or revert. Write the record with `status: skipped (existing modified branch)` and return.

## Run ports and browser

```bash
python3 <ws>/../../_core/data-root/run_claim.py port --ws ticket-execution --key <KEY> --kind dev   # DEV
python3 <ws>/../../_core/data-root/run_claim.py port --ws ticket-execution --key <KEY> --kind cdp   # CDP
node $B/scripts/browser.js start --profile <p> --port <CDP>
```

Each call returns the same port again, and stages 05 and 06 use the same ports and profile. Every browser call below carries `--profile <p>`, and `browser.js stop --profile <p>` stops it. Never use the default profile or port.

## Server

```bash
python3 <ws>/tools/dev_server.py up --app-root <app> --state $R/dev-server.json --port <DEV> --path <first review path>
```

Run it as a background shell command with no sandbox and full network, then wait for the JSON (up to 10 minutes on a fresh worktree). Use `port` from the JSON for every URL below. On exit 6 or 7, read `tail` and the log; do not edit code. An environment failure (AWS, database, VPN) is recorded, every row is "Not captured" with that reason, and the stage returns. Leave the server running when `up` succeeded.

## Capture

The shot names match stage 05 (`row<N>__<W>x<H>.png`, `<N>` the checklist row number, `<W>x<H>` its width and height), so stage 05 can pair them. Heights for widths: 1920x1080, 1440x900, 1100x800, 768x1024, 375x812.

| Check in plan | Command |
|---------------|---------|
| screenshot, measure | `node $B/scripts/screenshot.js --profile <p> --url "http://localhost:<port><path>" --viewports <W>x<H>,... [--selector '<css>'] --name row<N> --out-dir $R/shots --timeout 60000` |
| interact | The `interact.js` call with the row's steps, ending in `{"action":"screenshot","name":"row<N>__<W>x<H>"}`, and no `assert_*` step that depends on the change |

On a page that needs no login, the clean page is the baseline. Use `--timeout 60000` on the first call to a page; the first compile takes about 30 seconds. A baseline is a screenshot, not a check: no row is PASS or FAIL here, and an `assert_*` step is not run.

A baseline of a section the clean branch does not have yet (new component) is expected to be missing: `ELEMENT_NOT_FOUND` with a `--selector` row is "Not captured: not on the clean branch", not an error. Capture the full page for that row only when the row has no selector.

### Pages behind a login

Read the root's row in `<data-root>/workspaces/ticket-execution/repos.md` "Test logins". `L` is its steps file under `<data-root>/workspaces/ticket-execution/logins/`, and `S` is the secrets file that section names. Do not open `S`. One call per page and width signs in once and takes every shot of that page in the same tab:

```bash
node $B/scripts/interact.js --profile <p> --fresh-context --viewport <W>x<H> --timeout 60000 \
  --url "http://localhost:<port><login path>" --steps-file $L --secrets-file $S --out-dir $R/shots \
  --steps '[{"action":"goto","url":"http://localhost:<port><path>"}, {"action":"screenshot","name":"row<N>__<W>x<H>"}, ...]'
```

- The sign-in takes about 35 seconds. The number of sign-ins equals the number of distinct page and width pairs among the captured rows. A second sign-in for the same pair fails the Sign-ins audit row, with one exception: when a page's single call aborted on an overlay or selector error before any screenshot was taken, retry that page once. Record it as `sign-ins: N (1 retry on <page>)`. A retry that aborts again leaves the rows "Not captured" with the failed step.
- A sign-in done any other way, a root with no "Test logins" row, or a call that fails inside the steps file: "Not captured: needs login" with the failed step. A captcha that blocks the sign-in is recorded as such. Do not look for a bypass in the code or the env.
- `screenshot.js` opens new tabs without the session. On these pages use the `screenshot` step of `interact.js`.
- A row that sends a form is not captured when "Form submits" is not `yes`. Never fill or send a form for a baseline.

Open at least one screenshot per page to confirm it shows the page and not a login wall, an error overlay or a blank screen. When it does not, the row is "Not captured" with what the screenshot shows (a bad baseline misleads stage 05 more than a missing one).

## Finish

```bash
node $B/scripts/browser.js stop --profile <p>
```

Leave the dev server running: stage 05 reuses it for the same app root and reads `$R/dev-server.json` for `stop <KEY>`. Check `git -C <work tree> status --short` is still empty and `git diff --cached --name-only` is empty.

## Record

`R/baseline-record.md`. The first line is `version: 1`.

A captured run:

```markdown
version: 1

# <KEY> baseline

- status: captured
- branch: <name> (created from origin/<base> <hash> | existing at <hash>, no commits ahead)
- work tree: <main tree at root | worktree path>
- app root: <path>/code
- clean base: HEAD <hash> = origin/<base> <hash>; `git status --short` empty
- server: http://localhost:<port> from <app> (<started | reused>), left running
- browser: profile <p>, CDP <CDP>, stopped
- sign-ins: <N> (add `(1 retry on <page>)` when a page was retried once; 0 when no login)

## Baselines

| # | Line | Path | Widths | Files |
|---|------|------|--------|-------|
| 1 | <line> | `/model` | 1440, 375 | `shots/row1__1440x900.png`, `shots/row1__375x812.png` |

## Not captured
<Each row with the reason (not on the clean branch, needs login, form row, server failed). Or none.>
```

A skipped run:

```markdown
version: 1

# <KEY> baseline

- status: skipped (<no UI-checkable rows | form submits: no | existing modified branch>)
- detail: <one line: which check fired and what it saw, for example `3 commits ahead of origin/dev`>
- started: nothing (no claim, no server, no browser)
```

Write it with the Write or StrReplace tool, or with `tools/write_record.py --stage 03b --key <KEY>` when the chat is rooted outside this workspace (`../../shared/tools.md` "Writing records"). Return the record path and each audit row.
