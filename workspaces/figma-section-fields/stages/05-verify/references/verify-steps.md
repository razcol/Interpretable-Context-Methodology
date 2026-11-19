# Verify steps

Commands for stage 05. `<workspace>` is `/home/dev/ai-system/workspaces/figma-section-fields`. `B` is the browser-cdp skill folder (`/home/dev/ai-system/_core/skills/browser-cdp`), `R` is `<runs>/<node-id>/05-verify`, `S` is `<runs>/<node-id>/01-export`, and `$FIGMA` is the call in `shared/figma-cli-setup.md`. All three are absolute, so the commands run from any folder. Every script prints one JSON object.

## Run ports and browser

Other runs may verify at the same time, so this run uses only its own ports and browser profile. `<node-id>` is the run being verified (M on a mobile pass). Get them once (each call returns the same port again):

```bash
python3 <workspace>/../../_core/data-root/run_claim.py port --ws figma-section-fields --key <node-id> --kind dev   # DEV
python3 <workspace>/../../_core/data-root/run_claim.py port --ws figma-section-fields --key <node-id> --kind cdp   # CDP
node $B/scripts/browser.js start --profile $P --port <CDP>
```

`P` is `fsf-<node-id>`, the run's own profile: every browser call below carries `--profile $P`, and `browser.js stop --profile $P` stops it. Never use the default profile or port.

## Level 1: the export against Figma

```bash
node $B/scripts/screenshot.js --profile $P --url "file://$S/preview.html" --viewports <W>x<H> --name preview --out-dir $R/shots
node $B/scripts/diff.js --baseline $S/figma.png --current $R/shots/preview__<W>x<H>.png --out $R/shots/diff.png --max-diff-ratio 1
$FIGMA export '<figma-url>' --out $R/fluid.html --fluid
node $B/scripts/measure.js --profile $P --url "file://$R/fluid.html" --viewports 1920x1080,1440x900,1100x800 --name fluid --out-dir $R/shots
```

`<W>x<H>` is the PNG size of `figma.png` (the render is at scale 1). Record `diffRatio`. Missing fonts and image resampling move many pixels, so the ratio is a number to compare between runs, not a pass mark. Look at `diff.png` for misplaced blocks. The fluid preview must pass `measure.js` (exit 0).

## Level 2: the section in the app

The test route for the repo is in `<data-root>/workspaces/figma-section-fields/repos.md`. `<port>` is the server for this run's app root:

1. A server for this app root already answers: `curl -s -o /dev/null -w '%{http_code}' http://localhost:<DEV>/` (started earlier in this run), or the profile's `dev.port` when `ss -ltnp` shows the process on it runs from this app root (`readlink /proc/<pid>/cwd`). Use that port. A server on `dev.port` from another folder belongs to another run or app: leave it alone.
2. Otherwise start it from the app root in the background on the run's port: `PORT=<DEV> npm run dev`, and `<port>` is `<DEV>`. It loads its own environment and runs prisma; wait until the route answers (up to 3 minutes).
3. Measure the section. `#<order>` is the section's id on the page; read it from the page with `snapshot.js --mode dom` when it is not known:

```bash
node $B/scripts/measure.js --profile $P --url "http://localhost:<port><route>" --selector '<section selector>' --name app --out-dir $R/shots --timeout 60000
```

Exit 0 passes. Exit 11 means overflow; `error.details.results` gives `overflowPx` per width. A section that is not on the page (`ELEMENT_NOT_FOUND`) means the layout is not placed on that test page yet: report it, do not fail the code.

4. Hover: `interact.js` has no hover action. Compare the hover state by eye against Figma's hover variant on the preview and app shots. When a card toggles on click, use the harness and a click step as in the Mobile touch check.

## Desktop baseline for the mobile pass

On a desktop PASS, when the export record has `pair: <M>` or `pair: pending`, save the baseline shots. Use the harness (it is deterministic, and 05m uses the same page). `<harness root>` is the folder holding `components/`: the profile's `appRoot` plus `sectionsDir` without its `components/...` tail (for example `code/app`). `<props>` is `<runs>/<D>/05-verify/harness-props.json`: one object of `Client<Folder>` props in the shape the bound `Server<Folder>.js` passes, with texts from D's section map. Write it once; every harness build of the pair uses it.

```bash
(cd <workspace>/skills/next-section-repo && python3 scripts/harness.py --repo <harness root> --folder <Folder> --out-dir $R/harness --props <props>)
node $B/scripts/screenshot.js --profile $P --url "file://$R/harness/index.html" --viewports 1920x1080,1440x900,1100x800 --name baseline --out-dir $R/shots
```

This writes `$R/shots/baseline__1440x900.png` (and the other widths). Then ask the pair question once (stage CONTEXT step 7).

## Mobile

On a mobile pass, `S` is `<runs>/<M>/01-export`, `R` is `<runs>/<M>/05-verify`, and `<W>x<H>` is the PNG size of M's `figma.png`. `H` is the harness page `file://$R/harness/index.html`. `<page>` is `http://localhost:<port><route>`, or `H` when the app cannot start (a worktree without `node_modules` cannot). `<harness root>` and `<props>` are as in "Desktop baseline"; write the props file there when it is absent (Case B). `<trigger>` is the trigger selector the conform record lists for a reveal. The 1920/1440/1100 desktop checks above are not rerun; the regression check covers desktop.

```bash
# Level 1 mobile
node $B/scripts/screenshot.js --profile $P --url "file://$S/preview.html" --viewports <W>x<H> --name preview --out-dir $R/shots
node $B/scripts/diff.js --baseline $S/figma.png --current $R/shots/preview__<W>x<H>.png --out $R/shots/diff.png --max-diff-ratio 1
# Fluid mobile
$FIGMA export '<M url>' --out $R/fluid.html --fluid
node $B/scripts/measure.js --profile $P --url "file://$R/fluid.html" --viewports 320x700,375x812,<W>x900,768x1024,1279x800 --name fluid --out-dir $R/shots
# Harness H (always: regression and touch use it), then Level 2 on the app route, or on H when the app cannot start
(cd <workspace>/skills/next-section-repo && python3 scripts/harness.py --repo <harness root> --folder <Folder> --out-dir $R/harness --props <props>)
node $B/scripts/measure.js --profile $P --url "http://localhost:<port><route>" --selector '<section selector>' --viewports 320x700,375x812,<W>x900,768x1024,1279x800 --name app --out-dir $R/shots --timeout 60000
node $B/scripts/measure.js --profile $P --url "file://$R/harness/index.html" --selector '<section selector>' --viewports 320x700,375x812,<W>x900,768x1024,1279x800 --name harness --out-dir $R/shots
# Boundary
node $B/scripts/screenshot.js --profile $P --url "<page>" --viewports 1279x900,1280x900 --name boundary --out-dir $R/shots
# Desktop regression, after 04m
node $B/scripts/screenshot.js --profile $P --url "file://$R/harness/index.html" --viewports 1440x900 --name regression --out-dir $R/shots
# Case B only (baseline: from-head <sha>): rebuild the baseline from that commit
git -C <repo> worktree add $R/head <sha>
(cd <workspace>/skills/next-section-repo && python3 scripts/harness.py --repo $R/head/<harness root, relative to the repo> --folder <Folder> --out-dir $R/head-harness --props <props>)
node $B/scripts/screenshot.js --profile $P --url "file://$R/head-harness/index.html" --viewports 1440x900 --name regression__head --out-dir $R/shots
git -C <repo> worktree remove $R/head
node $B/scripts/diff.js --baseline <baseline> --current $R/shots/regression__1440x900.png --out $R/shots/regression-diff.png --max-diff-ratio 0.001
# Touch, once per reveal in the conform record (393x852, or M's <W>x<H>)
node $B/scripts/interact.js --profile $P --url "<page>" --viewport 393x852 --out-dir $R/shots --steps '[{"action":"screenshot","name":"touch-rest"},{"action":"click","selector":"<trigger>"},{"action":"screenshot","name":"touch-open"},{"action":"click","selector":"<trigger>"},{"action":"screenshot","name":"touch-closed"}]'
```

`<baseline>` is `<runs>/<D>/05-verify/shots/baseline__1440x900.png` (Case A) or `$R/shots/regression__head__1440x900.png` (Case B).

| Check | Pass |
|---|---|
| Level 1 mobile | `diffRatio` recorded |
| Fluid mobile | exit 0, no overflow |
| Level 2 or harness | exit 0 and the selector is found. On `H` the report says "harness: media and breadcrumbs stubbed" and never claims Level 2 |
| Boundary | 1279 shows mobile and 1280 shows desktop, else FAIL. A listed overlap does not fail ([mobile-patterns.md "Breakpoints"](../../../skills/next-section-repo/references/mobile-patterns.md#breakpoints)) |
| Desktop regression | `match: true` (ratio ≤ 0.001 for the section), or each difference listed with its cause |
| Touch | Matches the recorded decision: tap toggle opens then closes; always shown is visible at rest; hidden is absent. A tap below the fold scrolls the page, so judge `touch-closed` by the card's state, not by a page diff with `touch-rest` |
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
