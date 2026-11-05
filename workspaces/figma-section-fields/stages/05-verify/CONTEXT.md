# Stage 05: Verify

Check the result in a browser: the export against Figma's own picture, and the section in the running app at three widths. On a mobile pass, check the mobile widths, the 1279/1280 boundary, the desktop regression and the tap path.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-export/output/<node-id>/` | `export-record.md`, `figma.png`, `preview.html` | Figma URL, viewport, pair, baseline, reference image, preview |
| Stage 04 | `../04-conform-bind/output/<node-id>/conform-record.md` | Full file | What changed. Mobile: the touch decisions and triggers |
| Baseline | `output/<D>/shots/baseline__1440x900.png` | The file (mobile, Case A) | Desktop regression reference |
| Targets | `../../targets/repos.md` | The repo's test route | Where the section is placed |
| Steps | `references/verify-steps.md` | Full file, or "Mobile" on a mobile pass | Commands and pass marks |
| Harness | `../../skills/next-section-repo/scripts/harness.py` | Usage line | Deterministic page for baseline, regression and tap |
| Browser | `../../../../_core/skills/browser-cdp/SKILL.md` | "Checking a section export" | `screenshot.js`, `diff.js`, `measure.js`, `interact.js` |

## Process

1. Start the browser with browser-cdp `browser.js start`, or reuse it when it already runs (05m after 05). Headless only. On `viewport: mobile`, run the "Mobile" section of `references/verify-steps.md` instead of steps 2 to 4, then continue at step 5.
2. Level 1: follow `references/verify-steps.md` to screenshot the preview at the Figma size and diff it against `figma.png`. Then export the fluid preview and run `measure.js` on it at 1920, 1440 and 1100.
3. Level 2, when the repo has a test route and the route is not `element` without a page: check whether `http://localhost:<dev port>` answers. If not, run `npm run dev` from the repo's app root in the background and wait for it. Run `measure.js` on the route with `--selector` set to the section's element.
4. Compare the Level 2 screenshot with `figma.png` by eye for row order, hover and borders, and say what differs.
5. Write `output/<node-id>/verify-report.md` with PASS or FAIL per check.
6. On FAIL, go back to `../04-conform-bind/CONTEXT.md` with the failing checks (in mobile mode on a mobile pass). After a second FAIL on the same run, stop and show the report.
7. Desktop PASS with `pair: <M>` or `pair: pending`: save the baseline shots (`verify-steps.md` "Desktop baseline"). On `pair: pending`, ask once at the end: "Mobile design URL, or `mobile out of scope`?" Apply the answer as `shared/run-records.md` "Pair rules" says. With `pair: <M>`, load `../01-export/CONTEXT.md` for the mobile pass.
8. Stop the dev server only if this stage started it, and stop the browser.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 3 | The repo has no test route | Give a route (added to `targets/repos.md`), or skip Level 2 |
| 6 | A second FAIL | What to change, or accept |
| 7 | Desktop PASS on `pair: pending` | The mobile URL, or `mobile out of scope` |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Level 1 | The diff ratio is recorded and the fluid preview has no overflow at any width |
| Level 2 | No overflow at 1920, 1440 and 1100 on the test route, or the report says why Level 2 was skipped |
| Look | Row order, hover and borders match Figma in the screenshots, or each difference is listed |
| Baseline | Desktop PASS with a pair or `pair: pending`: `shots/baseline__1440x900.png` exists |
| Mobile widths | Mobile: diff ratio recorded, no overflow at 320, 375, M's width, 768 and 1279 |
| Harness label | Mobile: a harness result says media and breadcrumbs are stubbed and is not called Level 2 |
| Boundary | Mobile: 1279 shows mobile, 1280 desktop, and any mixed state at 1279 is listed |
| Regression | Mobile: the 1440 diff ratio is ≤ 0.001, or each difference is listed |
| Touch | Mobile: each recorded trigger behaves as its touch decision says |
| Clean up | No dev server, browser or `head` worktree this stage started is left |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Verify report | `output/<node-id>/verify-report.md` | Checks with PASS or FAIL, widths, diff ratio, screenshot paths |
| Screenshots | `output/<node-id>/shots/` | PNG |
| Baseline | `output/<D>/shots/baseline__<W>x<H>.png` | Harness shots at the desktop widths |
| Regression | `output/<M>/shots/regression__*.png`, `regression-diff.png` | The 1440 shot after 04m, the HEAD shot (Case B), the diff |
