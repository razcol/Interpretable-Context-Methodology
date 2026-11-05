# Verify steps

Commands for stage 05. `B` is the browser-cdp skill folder (`/home/dev/ai-system/_core/skills/browser-cdp`), `R` is `stages/05-verify/output/<node-id>`, `S` is `stages/01-export/output/<node-id>`, and `$FIGMA` is the call in `shared/figma-cli-setup.md`. Run browser-cdp scripts from `B`. Every script prints one JSON object.

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

4. Hover: `interact.js --url <route> --steps '[{"action":"screenshot","name":"rest"}]'`, then the same with a hover step on a card, to compare against Figma's hover variant.

## Desktop baseline for the mobile pass

On a desktop PASS, when the export record has `pair: <M>` or `pair: pending`, save the baseline shots. Use the harness (it is deterministic, and 05m uses the same page):

```bash
python3 skills/next-section-repo/scripts/harness.py --repo <app root> --folder <Folder> --out-dir $R/harness
node $B/scripts/screenshot.js --url "file://$R/harness/index.html" --viewports 1920x1080,1440x900,1100x800 --name baseline --out-dir $R/shots
```

This writes `$R/shots/baseline__1440x900.png` (and the other widths). Then ask the pair question once (stage CONTEXT step 7).

## Mobile

On a mobile pass, `S` is `stages/01-export/output/<M>`, `R` is `stages/05-verify/output/<M>`, and `<W>x<H>` is the PNG size of M's `figma.png`. `H` is the harness page: `file://$R/harness/index.html`, built as above with `--out-dir $R/harness`. The 1920/1440/1100 desktop checks above are not rerun; the regression row covers desktop.

| Check | How | Pass |
|---|---|---|
| Level 1 mobile | `screenshot.js --url "file://$S/preview.html" --viewports <W>x<H> --name preview`, then `diff.js --baseline $S/figma.png --current $R/shots/preview__<W>x<H>.png --out $R/shots/diff.png --max-diff-ratio 1` | `diffRatio` recorded |
| Fluid mobile | `$FIGMA export '<M url>' --out $R/fluid.html --fluid`, then `measure.js --url "file://$R/fluid.html" --viewports 320x700,375x812,<W>x900,768x1024,1279x800 --name fluid` | exit 0, no overflow |
| Level 2 or harness | `measure.js` with `--selector '<section selector>'` at the same widths on the app route (Level 2 steps above). When the app cannot start, on `H` | exit 0 and the selector is found. On `H` the report says "harness: media and breadcrumbs stubbed" and never claims Level 2 |
| Boundary | `screenshot.js` on the route or `H` with `--viewports 1279x900,1280x900 --name boundary` | 1279 shows mobile, 1280 shows desktop. In ora `bps.desktop` is `min-width: 1279px`, so both apply at 1279: list each `bps.desktop` rule of the section that is active there (the mixed state). Listed, it does not fail |
| Desktop regression | After 04m: `screenshot.js` on `H` with `--viewports 1440x900 --name regression`. Baseline, Case A: `stages/05-verify/output/<D>/shots/baseline__1440x900.png`. Case B (`baseline: from-head <sha>`): `git -C <repo> worktree add $R/head <sha>`, run the harness with `--repo $R/head/<app dir> --out-dir $R/head-harness`, shoot it with `--name regression__head`, then `git -C <repo> worktree remove $R/head`. Then `diff.js --baseline <baseline> --current $R/shots/regression__1440x900.png --out $R/shots/regression-diff.png --max-diff-ratio 0.001` | `match: true` (ratio ≤ 0.001 for the section), or each difference listed with its cause |
| Touch | For each reveal in the conform record: `interact.js --url <route or H> --viewport 393x852 --out-dir $R/shots` (or M's `<W>x<H>`) with steps: screenshot `touch-rest`, click the recorded trigger, screenshot `touch-open`, click it again, screenshot `touch-closed` | Matches the recorded decision: tap toggle opens then closes; always shown is visible at rest; hidden is absent |
| Look | The `touch-rest` and Level 2 (or `H`) shots at M's width against `$S/figma.png` by eye | Order, sizes and decor match, or each difference is listed |

Run browser-cdp scripts with `--out-dir $R/shots` unless the row says otherwise.

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
