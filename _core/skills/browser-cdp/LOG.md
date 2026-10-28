# browser-cdp Working Log

Append an entry every time the skill is used, even when it works. Record the command family, the target, the outcome, and anything surprising. Update `SKILL.md` when a pattern repeats.

## 2026-10-04 Initial build and test (skill-factory stage 04)

- Environment: WSL2 Ubuntu, Node 20.20, Chrome 147 at /usr/bin/google-chrome, headless.
- Tested against a local fixture page, example.com and news.ycombinator.com.
- Works: navigate, screenshot (viewport, full page, selector), capture, snapshot (a11y, dom, html, text), diff, interact, state (cookies, storage), stop/start.
- Determinism: identical sha256 for repeated screenshots of the fixture and of example.com at 3 viewports.
- Fixed during testing: a11y snapshot noise (duplicate text and false-valued props). Browser stop now uses CDP close so cookies are flushed.
- Not tested: Windows Chrome from WSL (skipped by request), authenticated real sites.

## 2026-10-04 Verification from the final folder

- Pinned `puppeteer-core` to 24.43.1. The first pick, 25.12.0, requires Node >= 22.12 and this machine has Node 20.20. Full fixture suite re-run on 24.43.1: same results and same screenshot hashes as before.
- Persistent cookies survive `browser.js stop` then `start`. Earlier SIGTERM-based stop lost them, so stop now closes Chrome over CDP first.
- A fresh agent completed 6 tasks from `SKILL.md` alone. Gaps it found were fixed: default output moved to `~/.cache/browser-cdp/out`, `--out-dir` and snapshot formats documented.
- Alternative evaluated and not chosen: `Bun.WebView` (needs Bun >= 1.4, experimental API, most capabilities would still be hand-built raw CDP). Revisit when it is stable and Bun 1.4 is the baseline.
- Open items: Windows Chrome from WSL (WSL2 NAT likely blocks it, mirrored networking would be needed), authenticated real sites, and whether a headed window is visible under WSLg (the headed run started and captured identical pixels, but visibility was not checked).

## 2026-10-04 Published to _core/skills/browser-cdp (skill-factory stage 06)

- Clean `npm ci` at the published path, no engine warnings on Node 20.20. Full fixture suite re-run from here.
- Found and fixed during post-publish verification:
  - Repeat visits returned HTTP 304 because the profile keeps an on-disk cache. Pages now open with the cache disabled, so `status` is 200 and results do not depend on cache state. Screenshot hashes did not change.
  - `interact.js` could pick a Chrome-internal page (`chrome://omnibox-popup...`) as "the current tab" and fail follow-up calls. It now only considers http(s), file and blank tabs.
- Still open: Windows Chrome from WSL, authenticated real sites, headed window visibility under WSLg, and whether `Bun.WebView` becomes a better base once stable.

## 2026-10-05 Headed login test on localhost:3000 (ID + OTP + Turnstile), in progress

- Started `browser.js start --headed --profile login-test --port 9444` under WSLg. Headed launch works; user watches the window.
- Surprise: only `browser.js` accepts `--port`. `interact.js`, `snapshot.js` take `--profile` only (passing `--port` gives USAGE). SKILL.md says "Use `--profile NAME --port N`", which reads as applying to every script.
- Surprise: `snapshot.js --url` and other `--url` calls open a fresh tab, so they do not show the live multi-step login state. Use `interact.js` without `--url` to continue in the current tab.
- Surprise: `interact.js` has no way to list buttons or evaluate JS. Selector `form button` only matches step 1. Later steps needed `button:not([disabled]):last-child`. The first match of a generic `button` can be the "back" button.
- Worked: typing the ID, scrolling the terms box with `click p` plus `press End/PageDown`, ticking the checkbox with `input[type=checkbox]`, typing a 6-digit OTP with six `press` steps.
- Turnstile appeared only after submitting the OTP, as a visible "Verify you are human" checkbox inside a cross-origin iframe. The skill cannot click it (and should not solve captchas). Left for the human to tick in the headed window.
- Dev server showed a transient Next.js build error (He.json invalid JSON) while the user was editing. Unrelated to the skill.

## 2026-10-05 Workato APIM existence check (self-service-cfs, Q1), inconclusive

- Ran `navigate.js --url https://apim.workato.com/colmobil--dev/cfs-self-service-v1/<Endpoint>` for 13 real endpoints plus one made-up name. No token sent (navigate.js is GET-only, cannot set headers).
- Result: all 14 returned HTTP 401, including the made-up name. APIM checks the token before routing, so this cannot tell existing from missing endpoints.
- Lesson: unauthenticated GET through this skill cannot prove an API endpoint exists. Needs a token-bearing POST (not a browser-cdp capability) or a logged-in Workato dashboard profile.

## 2026-10-05 Self-service-cfs B1 fix test (login + screens) on localhost:3000

- Logged in headless with profile `cfs-test` (ID step, terms step, 6 x `press 1`, submit). Worked without Turnstile because the dev server bypasses it. Then `goto` on /earlyPayment, /loanTracks, /loanTransactions, /creditReport in the same tab (sessionStorage survives `goto`, but `snapshot.js --url` / `state.js storage-get` use a fresh tab and cannot see it).
- Surprise: on a styled page `.creditReport button` did not match although `body button` did; `.creditReport p + *` clicked the real button. `[role=dialog]` never matched the result modal; `wait_for` with `text` works.
- Surprise: `interact.js` prints `consoleErrors` of several KB per React warning; filter with python. No way to see request bodies; worked around with a temporary `console.error` in the app (removed afterwards).

## 2026-10-05 Self-service-cfs gf-retest, report screenshots, B3 check

- Same login flow as the B1 entry. `interact.js` has no `sleep` action (allowed: goto, click, type, press, select, wait_for, get_text, assert_text, assert_url, screenshot); put `time.sleep` between separate calls from python. Build `--steps` with `json.dumps` (two hand-quoted attempts were invalid JSON).
- `wait_for` on a text that is not on the page waits the full 30 s then returns TIMEOUT; check the real post-login text first.
- Div-based buttons (ActionRow, `div[dir=rtl]` with inline style) did not click via a style-attribute selector; could not capture the error modal on /earlyPayment and total loss.
- B3 check: after a submit that Workato answers with ErrorCode `Error`, `assert_url contains /login` passes (session guard logged out).

## 2026-10-06 Self-service-cfs GenericForm retest after Workato fix

- Clicks on fixed-bottom elements silently hit the cookie banner (click uses coordinates, no scroll when already in viewport); the click "succeeds" but nothing happens. Fix: `state.js storage-set --area local --key cookieBannerDismissed --value 1 --url <origin>` (localStorage is shared across tabs), then reload.
- `div[style*='gap'] > div[dir=rtl]` selects the ActionRow; `button[dir=rtl]` selects DocumentRow. `button:last-of-type` opens the nav menu, not the cookie banner.
- `consoleErrors` is only returned when the run succeeds; on a failed step the console output is lost, so re-run after fixing the selector.

## 2026-10-06 Self-service-cfs UI QA (public surface only), localhost:3000

- Used `screenshot.js` (6 viewports), `capture.js`, `navigate.js` (21 routes), `snapshot.js --mode html/dom`, `interact.js` (validation and link flows). Profile `cfs-qa`, removed afterwards.
- Worked: `screenshot.js --selector` is the only way to measure layout offsets (image width/position); `snapshot.js --mode html` keeps SSR inline styles, useful to confirm markup is symmetric.
- Surprise: no way to read computed styles or bounding boxes; a layout offset (+60px) could be shown but not root-caused. A `measure`/`eval` step would help.
- Surprise: `navigate.js` reports HTTP 200 for protected routes that client-redirect to `/login`; use `finalUrl`.
- Blocked: authenticated screens need a test customer ID that is not stored anywhere by design.

## 2026-10-06 Self-service-cfs UI QA pass 2 (logged in), localhost:3000

- Logged in with `interact.js` (ID, terms, six `press 1`), then one `goto` per page in the same tab; `--viewport` on `interact.js` changes the size per call, so responsive checks worked without a separate script. `text/<visible text>` selectors work for `click`.
- Surprise: the image viewer once returned a stale picture for a file name that had been read before (a re-used name); use a new name per capture and compare file sizes.
- Surprise: `screenshot` in `interact.js` is viewport-only. Tall pages need a tall `--viewport` or `press End`; the footer stays below the fold on short pages.
- Surprise: data pages take 5 to 60 s on dev (`/earlyPayment` 20 s+); a fixed sleep between a `goto` call and the screenshot call was needed. `wait_for` timeouts of 30 s kill the whole call.
- Session expires after 15 min (app `AppTimeout`); a `goto` then lands on `/login` and `wait_for` text times out. Re-login first.
- Not possible with the skill: reading computed styles or bounding boxes (needed to root-cause a 60px offset), and watching network calls of a logged-in tab.

## 2026-10-06 — self-service-cfs-next UI QA fix verification (pass 3)
- Used `browser.js start --profile cfs-qa`, `interact.js` for the login flow, and a small puppeteer-core probe (in the project's audit/verify folder) to evaluate DOM/CSS, measure bidi character positions and run footer-overlap checks.
- Surprises: the app logs out after 15 min idle, so long sweeps silently turned into /login redirects (check `document.title`/URL in each result). `page.screenshot` files sometimes appeared a moment after the command returned. Element screenshots of a tall `section` were offset; use viewport or full-page shots instead.
- Request interception was used to abort the Workato call so an error modal could be opened without sending a request.

## 2026-10-06 self-service-cfs-next inline-style migration check
- Used: browser.js start/stop, interact.js (login flow across ID/terms/OTP in one tab, screenshots at 1280x800 and 375x812), diff.js for before/after comparison, 34 screenshots per run.
- Outcome: works. Before/after diffs were pixel-identical except one real difference (OTP input borders).
- Surprises: (1) screenshot.js tabs lose sessionStorage, so authenticated pages need interact.js in one tab. (2) Several times the tab froze on a click ("Runtime.callFunctionOn timed out"); `browser.js stop && start` fixed it, probably stale tabs piling up. (3) click with a Hebrew aria-label attribute selector hung once; plain CSS selectors were fine. (4) PerfectScrollbar scroll gates can be opened with click + press End.

## 2026-10-13 self-service-cfs-next login + OTP screens QA (localhost:3000, dev mode)
- Used browser.js start/stop (profile cfs-login-qa, removed afterwards) and a puppeteer-core harness (project audit/login-otp-qa-2026-10-13/) attached over CDP: request interception to mock Workato replies, count requests, real ClipboardEvent paste.
- Surprise: CDP `Input.insertText` does not fire a paste event, so it gave false results for react-otp-input; dispatch a real `ClipboardEvent('paste')` with a DataTransfer instead.
- Surprise: `waitForFunction` on a selector that disappears after success waits the full timeout.
- Real backend accepted a wrong OTP (000000) in the dev env, so real wrong-code behaviour could not be observed.

## 2026-10-13 self-service-cfs-next network audit (repeated/slow calls), localhost:3000
- Used an already-running Chrome on 9333 (`browser.js start` returned PORT_IN_USE) plus a puppeteer-core script attached over CDP using `Network.*` events with initiator stacks; one real login, client navigation over 14 routes, 3 hard reloads, 60 s idle.
- Gap: `capture.js --include-requests` has no timings, initiators, bodies or multi-step/logged-in support, so it could not do this job. A `network.js` (HAR-like capture across an interact.js flow) would cover it.
- Surprise: a synthetic `visibilitychange` dispatched on `document` (non-bubbling) does not reach react-query's window listener, so focus refetch could not be tested this way.

## 2026-10-13 self-service-cfs-next (localhost:3000, authenticated flow)
- Attempted: OTP login flow + navigation across protected pages, counting Workato API calls.
- Outcome: worked. Login via interact.js across 3 calls in the same tab.
- Surprises: no script lists successful requests in a persistent tab (capture.js opens a fresh tab, which loses sessionStorage-based login). Workaround: temporary console.error in app code, read from interact.js consoleErrors. A `--log-requests` flag on interact.js would help.
- Default port 9333 was occupied by an unrelated Chrome; started on --port 9334.
- Terms scroll gate (perfect-scrollbar onYReachEnd) passed by clicking the last element inside the scroll area.
