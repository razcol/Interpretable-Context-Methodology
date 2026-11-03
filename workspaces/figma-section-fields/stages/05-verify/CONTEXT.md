# Stage 05: Verify

Check the result in a browser: the export against Figma's own picture, and the section in the running app at three widths.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-export/output/<node-id>/` | `export-record.md`, `figma.png`, `preview.html` | Figma URL, reference image, preview |
| Stage 04 | `../04-conform-bind/output/<node-id>/conform-record.md` | Full file | What changed |
| Targets | `../../targets/repos.md` | The repo's test route | Where the section is placed |
| Steps | `references/verify-steps.md` | Full file | Commands and pass marks |
| Browser | `../../../../_core/skills/browser-cdp/SKILL.md` | "Checking a section export" | `screenshot.js`, `diff.js`, `measure.js` |

## Process

1. Start the browser with browser-cdp `browser.js start`. Headless only.
2. Level 1: follow `references/verify-steps.md` to screenshot the preview at the Figma size and diff it against `figma.png`. Then export the fluid preview and run `measure.js` on it at 1920, 1440 and 1100.
3. Level 2, when the repo has a test route and the route is not `element` without a page: check whether `http://localhost:<dev port>` answers. If not, run `npm run dev` from the repo's app root in the background and wait for it. Run `measure.js` on the route with `--selector` set to the section's element.
4. Compare the Level 2 screenshot with `figma.png` by eye for row order, hover and borders, and say what differs.
5. Write `output/<node-id>/verify-report.md` with PASS or FAIL per check.
6. On FAIL, go back to `../04-conform-bind/CONTEXT.md` with the failing checks. After a second FAIL on the same run, stop and show the report.
7. Stop the dev server only if this stage started it, and stop the browser.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 3 | The repo has no test route | Give a route (added to `targets/repos.md`), or skip Level 2 |
| 6 | A second FAIL | What to change, or accept |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Level 1 | The diff ratio is recorded and the fluid preview has no overflow at any width |
| Level 2 | No overflow at 1920, 1440 and 1100 on the test route, or the report says why Level 2 was skipped |
| Look | Row order, hover and borders match Figma in the screenshots, or each difference is listed |
| Clean up | No dev server or browser this stage started is left running |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Verify report | `output/<node-id>/verify-report.md` | Checks with PASS or FAIL, widths, diff ratio, screenshot paths |
| Screenshots | `output/<node-id>/shots/` | PNG |
