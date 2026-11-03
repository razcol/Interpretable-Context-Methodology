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

## The report

```markdown
# Verify report <node-id>
- result: PASS | FAIL
- level 1: diffRatio <n>, fluid overflow <none | widths>
- level 2: route <route>, overflow <none | widths>, or skipped: <why>
- look: <row order, hover, borders: same as Figma, or each difference>
- shots: <paths>
```
