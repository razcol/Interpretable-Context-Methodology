---
name: browser-cdp
description: "Drive a real Chrome browser through fixed, JSON-in/JSON-out scripts built on the Chrome DevTools Protocol. Use for visual tests (screenshots at set viewports, baseline diffs), gathering page context (DOM, accessibility tree, text, console and network errors), scripted interaction (click, type, forms), and cookie/storage handling, on localhost or external sites."
status: provisional (approved 2026-10-04, tested on fixtures and public pages, WSL Chrome headless only)
license: N/A (internal)
---

# Browser CDP

Agents pick a script and fill in arguments. They never write raw CDP or Puppeteer code.
Every script prints exactly one JSON object and exits non-zero on failure.

## Status: provisional

Tested so far: headless Chrome inside WSL2, fixture pages, and public pages.
Not tested: Windows Chrome from WSL, authenticated real sites. Headed mode starts and captures correctly under WSLg, but window visibility was not checked.
**Every time this skill is used, append to `LOG.md`** (what was attempted, outcome, surprises). If you were told not to modify the skill folder, put the same note in your own report instead.

## First-time setup

Read `references/setup.md` once. Short version: `cd` to this skill folder, run `npm install`, confirm Chrome exists.

## Start and stop the browser

Scripts attach to one long-lived Chrome, so cookies and the open tab survive between calls.

```bash
node scripts/browser.js start            # headless, profile "default", port 9333
node scripts/browser.js status
node scripts/browser.js stop
```

Use `--profile NAME --port N` for a separate login/identity. Each profile has its own cookie jar on disk.

## Which script to run

| Need | Script | Key arguments | You get |
|------|--------|---------------|---------|
| Is this page reachable and ready? | `navigate.js` | `--url` | status, final URL, title, ready time |
| Screenshot(s) | `screenshot.js` | `--url`, `--viewports 375x812,1280x800`, `--full-page` or `--selector` | PNG paths, sizes, sha256 |
| Console, page errors, failed/4xx requests | `capture.js` | `--url`, `--out details.json` | counts plus the first 50 of each |
| Page structure for reasoning | `snapshot.js` | `--url`, `--mode a11y\|dom\|html\|text`, `--selector` | file path plus stats |
| Compare two screenshots | `diff.js` | `--baseline`, `--current`, `--max-diff-ratio`, `--init` | match, diff ratio, diff PNG |
| Does a local page scroll sideways? | `measure.js` | `--url` (localhost or file:// only), `--viewports 1920x1080,1440x900,1100x800`, `--selector` | per viewport: `scrollWidth`, `innerWidth`, `overflowPx`, section box, screenshot |
| Click, type, submit, assert | `interact.js` | `--steps '[...]'`, optional `--url` | per-step results, console errors |
| Cookies and localStorage | `state.js` | `cookies-get`, `cookies-set`, `storage-get`, ... | redacted values by default |

Snapshot modes:
- `a11y`: "what can a user do here". A JSON list of `{depth, role, name, value?, props?}`. Pages with no semantic headings will have none in this list.
- `dom`: element tree with ids, classes and key attributes. Use it to find selectors and headings (`--max-depth` limits size).
- `text`: the readable content as plain text.
- `html`: raw markup, only when you need it.

## Where output goes

Screenshots, snapshots and `interact.js` screenshots are written to `--out-dir DIR`. The default is `~/.cache/browser-cdp/out` (or `$BCDP_OUT`), never the skill folder. `snapshot.js` and `capture.js` also accept `--out FILE` for an exact path. The JSON result always carries the real paths.

## Output contract

Success: `{"ok": true, ...}` and exit 0. Failure: `{"ok": false, "error": {"code", "message", "details"?}}`.

| Exit | Code examples | Meaning |
|------|---------------|---------|
| 1 | USAGE, FILE_NOT_FOUND | Bad arguments. Fix the call. |
| 2 | BROWSER_NOT_RUNNING, BROWSER_UNREACHABLE | Run `browser.js start`. |
| 3 | NAVIGATION_FAILED | Page unreachable (DNS, refused, bad TLS). |
| 4 | ELEMENT_NOT_FOUND | Selector not present within `--timeout`. |
| 5 | TIMEOUT | Navigation or wait exceeded `--timeout` (default 30000 ms). |
| 6 | ASSERTION_FAILED | An `assert_*` step did not hold. |
| 10 | DIFF_DETECTED | Only with `diff.js --fail-on-diff`. |
| 11 | OVERFLOW_DETECTED | `measure.js`: at least one viewport scrolls sideways. `error.details` holds the full per-viewport result. |
| 99 | INTERNAL | Unexpected. Log it in `LOG.md`. |

An HTTP 404 or 500 is not a script failure. Check `status` in the JSON.

## Determinism rules (already built in, do not fight them)

- Each screenshot, snapshot, capture and navigate call opens a fresh tab and closes it after.
- Device scale factor 1, animations and transitions disabled, reduced motion on, fonts awaited, network idle awaited.
- File names are `<name>__<W>x<H>[__full|__sel-x].png`. Same command, same names.
- Page text, time, ads and other live content can still change pixels. For diffs on live sites use `--max-diff-ratio` and compare against a baseline from the same machine.

## Interaction steps

`interact.js` reuses the current tab, so a login flow can span several calls. It stops at the first failing step and reports `failedStep`.
Actions: `goto`, `click`, `type`, `press`, `select`, `wait_for` (selector or text), `get_text`, `assert_text`, `assert_url`, `screenshot`.
Full examples: `references/recipes.md`.

## Secrets

- `state.js` hides cookie and storage values on stdout. `--show-values` prints them. Avoid it.
- `--out` files contain real values (mode 0600). Keep them out of git and out of your replies.
- Never put tokens in commands, scripts or this folder. Log in once in a dedicated profile (see recipes) and let the profile hold the session.
- Chrome 136+ ignores debug ports on the default profile, so these scripts always use their own profile directory under `~/.cache/browser-cdp/profiles/`.

## Files

- `references/setup.md`: install and verify
- `references/recipes.md`: the first test case, visual regression loop, login reuse, data gathering
- `references/troubleshooting.md`: common failures and fixes
- `fixtures/`: a local test page and server plus `run-all.sh`, `run-extra.sh`, `run-persist.sh` to re-verify the scripts after any change
- `LOG.md`: usage log, keep updating

## Checking a section export

A section exported from Figma is verified at two levels.

- **Level 1, export fidelity.** Screenshot the figma-cli HTML preview (`file://`) at the Figma frame size with `screenshot.js`, then `diff.js --baseline <figma-cli render PNG> --current <screenshot> --max-diff-ratio 1`. Report `diffRatio`. Fonts that are not installed and image smoothing move many pixels, so treat it as a number to compare between runs, not a pass mark.
- **Level 2, in the app.** Run `measure.js --url http://localhost:3000/<route> --selector '#<order>'` at 1920, 1440 and 1100. Exit 0 means no horizontal overflow at any width. Exit 11 means it overflows; `error.details.results` says where and by how much.

`measure.js` refuses any URL that is not `http://localhost`, `http://127.0.0.1` or `file://`. Its fixtures test is `bash fixtures/run-measure.sh [OUT_DIR]` with the browser started.

