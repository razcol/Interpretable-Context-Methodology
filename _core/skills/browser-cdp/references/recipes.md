# Recipes

All commands run from the skill folder. Replace URLs and paths. Read `SKILL.md` first.

## 1. Responsive screenshots plus console errors (the baseline test case)

```bash
node scripts/browser.js start
node scripts/screenshot.js --url https://example.com/ --viewports 375x812,768x1024,1280x800 --out-dir ./out
node scripts/capture.js --url https://example.com/ --out ./out/example-capture.json
```

Check `screenshots[].path` exists and `summary.consoleErrors`, `summary.pageErrors`, `summary.httpErrors` in the capture result.
`capture.js` ignores `favicon.ico` failures on purpose.

## 2. Visual regression loop

```bash
# first run: create the baseline
node scripts/screenshot.js --url http://localhost:3000/ --name home --out-dir ./shots/current
node scripts/diff.js --baseline ./shots/baseline/home__1280x800.png --current ./shots/current/home__1280x800.png --init

# later runs: compare
node scripts/screenshot.js --url http://localhost:3000/ --name home --out-dir ./shots/current
node scripts/diff.js --baseline ./shots/baseline/home__1280x800.png --current ./shots/current/home__1280x800.png --max-diff-ratio 0.001
```

- `match: false` with `reason: "size-mismatch"` means the page height or viewport changed. Treat it as a real change.
- When `diffImage` is returned, open it to see where pixels changed. Red marks differences.
- Accept a change by copying the current PNG over the baseline. Do that only with the user's approval.
- Mask live content (clocks, ads) by screenshotting a `--selector` instead of the whole page.

## 3. Fill a form and verify the result

```bash
node scripts/interact.js --new-tab --url http://localhost:3000/signup --steps '[
  {"action":"type","selector":"#name","text":"Ada"},
  {"action":"select","selector":"#plan","value":"pro"},
  {"action":"click","selector":"#submit"},
  {"action":"wait_for","text":"Welcome, Ada"},
  {"action":"assert_url","contains":"/welcome"},
  {"action":"screenshot","name":"signup-done"}
]'
```

The response lists each step and any console errors raised during the flow. On failure, `error.details.failedStep` and `completed` show where it stopped.
For long flows, put the JSON in a file and use `--steps-file flow.json`.

## 4. Log in once, reuse the session

1. Start a dedicated headed profile so a human can sign in: `node scripts/browser.js start --headed --profile work --port 9444`.
2. The human logs in in that window. Do not type passwords through scripts.
3. Stop and restart headless if desired: `node scripts/browser.js stop --profile work`, then `start --profile work --port 9444`.
4. Pass `--profile work` to every later command. Cookies live in the profile directory.

Session cookies (no expiry) may not survive a restart. Persistent cookies do. Check with `state.js cookies-get --profile work --domain example.com` and read `expires`.

### 4b. Scripted test login (local dev server, test identity)

For a test identity on a local dev server only, not a real account. The steps live in a file with `"secret"` keys; the values live in a secrets file outside every repo.

```bash
node scripts/interact.js --fresh-context --url http://localhost:3000/login \
  --steps-file <login-steps.json> --secrets-file ~/.config/ticket-execution/test-logins.env \
  --steps '...'   # or append the page check to the same steps file
```

An app that keeps its session in `sessionStorage` loses it in every new tab. Then the login and the page check must run in one tab: one `--fresh-context` call with the login steps followed by `goto` and the checks, or a `--new-tab` login call followed by calls without `--new-tab`, which continue in that tab.

## 5. Gather information from a page

```bash
node scripts/snapshot.js --url https://example.com/docs --mode a11y     # what a user can see and do
node scripts/snapshot.js --url https://example.com/docs --mode text     # readable content
node scripts/snapshot.js --url https://example.com/docs --mode dom --selector main --max-depth 6
node scripts/interact.js --url https://example.com/docs --steps '[{"action":"get_text","selector":"h1"}]'
```

Snapshots are written to files. Read only the parts you need.

## 6. Cookies and storage

```bash
node scripts/state.js cookies-get --domain example.com                 # values redacted
node scripts/state.js cookies-get --domain example.com --out ./secret/cookies.json
node scripts/state.js cookies-set --file ./secret/cookies.json
node scripts/state.js storage-get --url https://example.com/           # keys plus redacted values
node scripts/state.js cookies-clear --domain example.com
```

`./secret/` must be gitignored.
