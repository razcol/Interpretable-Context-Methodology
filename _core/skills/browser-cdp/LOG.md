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
