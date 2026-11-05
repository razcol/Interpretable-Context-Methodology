# Verify steps

Commands for stage 05. `<workspace>` is `/home/dev/ai-system/workspaces/figma-section-fields`. `B` is the browser-cdp skill folder (`/home/dev/ai-system/_core/skills/browser-cdp`), `R` is `<workspace>/stages/05-verify/output/<node-id>`, `S` is `<workspace>/stages/01-export/output/<node-id>`, and `$FIGMA` is the call in `shared/figma-cli-setup.md`. All three are absolute, so the commands run from any folder. Every script prints one JSON object.

## Level 1: the export against Figma

```bash
node $B/scripts/screenshot.js --url "file://$S/preview.html" --viewports <W>x<H> --name preview --out-dir $R/shots
node $B/scripts/diff.js --baseline $S/figma.png --current $R/shots/preview__<W>x<H>.png --out $R/shots/diff.png --max-diff-ratio 1
$FIGMA export '<figma-url>' --out $R/fluid.html --fluid
node $B/scripts/measure.js --url "file://$R/fluid.html" --viewports 1920x1080,1440x900,1100x800 --name fluid --out-dir $R/shots
```

`<W>x<H>` is the PNG size of `figma.png` (the render is at scale 1). Record `diffRatio`. Missing fonts and image resampling move many pixels, so the ratio is a number to compare between runs, not a pass mark. Look at `diff.png` for misplaced blocks. The fluid preview must pass `measure.js` (exit 0).

## Level 2: the section in the app

The test route for the repo is in `targets/repos.md`. The dev port is `dev.port` in the profile (3000 unless the script sets one).

1. `curl -s -o /dev/null -w '%{http_code}' http://localhost:<port>/` answers: use that server.
2. Otherwise start it from the app root in the background: `npm run dev`. It loads its own environment and runs prisma; wait until the route answers (up to 3 minutes). If another app already holds the port, use `PORT=3001 npm run dev` and port 3001.
3. Measure the section. `#<order>` is the section's id on the page; read it from the page with `snapshot.js --mode dom` when it is not known:

```bash
node $B/scripts/measure.js --url "http://localhost:<port><route>" --selector '<section selector>' --name app --out-dir $R/shots --timeout 60000
```

Exit 0 passes. Exit 11 means overflow; `error.details.results` gives `overflowPx` per width. A section that is not on the page (`ELEMENT_NOT_FOUND`) means the layout is not placed on that test page yet: report it, do not fail the code.

4. Hover: `interact.js` has no hover action. Compare the hover state by eye against Figma's hover variant on the preview and app shots. When a card toggles on click, use the harness and a click step as in the Mobile touch check.

## Desktop baseline for the mobile pass

On a desktop PASS, when the export record has `pair: <M>` or `pair: pending`, save the baseline shots. Use the harness (it is deterministic, and 05m uses the same page):

```bash
(cd <workspace>/skills/next-section-repo && python3 scripts/harness.py --repo <app root> --folder <Folder> --out-dir $R/harness [--props <json>])
node $B/scripts/screenshot.js --url "file://$R/harness/index.html" --viewports 1920x1080,1440x900,1100x800 --name baseline --out-dir $R/shots
```

This writes `$R/shots/baseline__1440x900.png` (and the other widths). Then ask the pair question once (stage CONTEXT step 7).

## Mobile

On a mobile pass, `S` is `<workspace>/stages/01-export/output/<M>`, `R` is `<workspace>/stages/05-verify/output/<M>`, and `<W>x<H>` is the PNG size of M's `figma.png`. `H` is the harness page `file://$R/harness/index.html`. `<page>` is `http://localhost:<port><route>`, or `H` when the app cannot start. `<trigger>` is the trigger selector the conform record lists for a reveal. The 1920/1440/1100 desktop checks above are not rerun; the regression check covers desktop.

```bash
# Level 1 mobile
node $B/scripts/screenshot.js --url "file://$S/preview.html" --viewports <W>x<H> --name preview --out-dir $R/shots
node $B/scripts/diff.js --baseline $S/figma.png --current $R/shots/preview__<W>x<H>.png --out $R/shots/diff.png --max-diff-ratio 1
# Fluid mobile
$FIGMA export '<M url>' --out $R/fluid.html --fluid
node $B/scripts/measure.js --url "file://$R/fluid.html" --viewports 320x700,375x812,<W>x900,768x1024,1279x800 --name fluid --out-dir $R/shots
# Harness H (always: regression and touch use it), then Level 2 on the app route, or on H when the app cannot start
(cd <workspace>/skills/next-section-repo && python3 scripts/harness.py --repo <app root> --folder <Folder> --out-dir $R/harness [--props <json>])
node $B/scripts/measure.js --url "http://localhost:<port><route>" --selector '<section selector>' --viewports 320x700,375x812,<W>x900,768x1024,1279x800 --name app --out-dir $R/shots --timeout 60000
node $B/scripts/measure.js --url "file://$R/harness/index.html" --selector '<section selector>' --viewports 320x700,375x812,<W>x900,768x1024,1279x800 --name harness --out-dir $R/shots
# Boundary
node $B/scripts/screenshot.js --url "<page>" --viewports 1279x900,1280x900 --name boundary --out-dir $R/shots
# Desktop regression, after 04m
node $B/scripts/screenshot.js --url "file://$R/harness/index.html" --viewports 1440x900 --name regression --out-dir $R/shots
# Case B only (baseline: from-head <sha>): rebuild the baseline from that commit
git -C <repo> worktree add $R/head <sha>
(cd <workspace>/skills/next-section-repo && python3 scripts/harness.py --repo $R/head/<app dir> --folder <Folder> --out-dir $R/head-harness [--props <json>])
node $B/scripts/screenshot.js --url "file://$R/head-harness/index.html" --viewports 1440x900 --name regression__head --out-dir $R/shots
git -C <repo> worktree remove $R/head
node $B/scripts/diff.js --baseline <baseline> --current $R/shots/regression__1440x900.png --out $R/shots/regression-diff.png --max-diff-ratio 0.001
# Touch, once per reveal in the conform record (393x852, or M's <W>x<H>)
node $B/scripts/interact.js --url "<page>" --viewport 393x852 --out-dir $R/shots --steps '[{"action":"screenshot","name":"touch-rest"},{"action":"click","selector":"<trigger>"},{"action":"screenshot","name":"touch-open"},{"action":"click","selector":"<trigger>"},{"action":"screenshot","name":"touch-closed"}]'
```

`<baseline>` is `<workspace>/stages/05-verify/output/<D>/shots/baseline__1440x900.png` (Case A) or `$R/shots/regression__head__1440x900.png` (Case B).

| Check | Pass |
|---|---|
| Level 1 mobile | `diffRatio` recorded |
| Fluid mobile | exit 0, no overflow |
| Level 2 or harness | exit 0 and the selector is found. On `H` the report says "harness: media and breadcrumbs stubbed" and never claims Level 2 |
| Boundary | 1279 shows mobile and 1280 shows desktop, else FAIL. A listed ora overlap does not fail ([mobile-patterns.md "Breakpoints"](../../../skills/next-section-repo/references/mobile-patterns.md#breakpoints)) |
| Desktop regression | `match: true` (ratio ≤ 0.001 for the section), or each difference listed with its cause |
| Touch | Matches the recorded decision: tap toggle opens then closes; always shown is visible at rest; hidden is absent |
| Look | By eye, the `touch-rest` and Level 2 (or `H`) shots at M's width match `$S/figma.png` in order, sizes and decor, or each difference is listed |

## The report

```markdown
# Verify report <node-id>
- result: PASS | FAIL
- level 1: diffRatio <n>, fluid overflow <none | widths>
- level 2: route <route>, overflow <none | widths>, or skipped: <why>
- look: <row order, hover, borders: same as Figma, or each difference>
- shots: <paths>
```

A mobile report adds, in place of the level 2 line:

```markdown
- pair: <D>
- fluid mobile: overflow <none | widths>
- level 2: route <route>, overflow <none | widths>, or harness: media and breadcrumbs stubbed
- boundary: 1279 <mobile | mixed: rules>, 1280 <desktop>
- desktop regression: baseline <path | from-head sha>, ratio <n>, <match | each difference>
- touch: <per trigger: decision, result>
```
