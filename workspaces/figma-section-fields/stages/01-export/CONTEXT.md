# Stage 01: Export

Read the repo's structure, read the Figma layer, and write the repo-shaped scaffold into this run's staging folder. A mobile pass (01m) writes the viewport map and the mobile overlay instead. Nothing is written into the repo here.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Run | The trigger message | Route, Figma URL, repo, folder (`sync`, `resync`, `mobile`), `--mobile <url>`, `--mobile` (`resync`, `element`), target file (`element`) | What this run is |
| Targets | `../../targets/repos.md` | Full file | Repo root and default repo |
| Repo skill | `../../skills/next-section-repo/SKILL.md` | `probe_repo.py` section | The repo profile |
| Setup | `../../shared/figma-cli-setup.md` | Full file | How to call figma-cli and load the token |
| Contract | `../../shared/export-contract.md` | Full file | Commands, notes and exit codes |
| Records | `../../shared/run-records.md` | `export-record.md`, pair rules | Record format, `pair:` values |
| Pair (01m) | `output/<D>/export-record.md`, `../04-conform-bind/output/<D>/class-map.json` | Full files | D's URL, folder, flags, section map, renamed classes |
| Map (01m) | `references/viewport-map.md` | Full file | Reading and editing the viewport map |

## Process

D is the desktop node id and M the mobile one. `$FIGMA` paths are from the workspace root, `<workspace>` (`/home/dev/ai-system/workspaces/figma-section-fields`); the skill scripts run from `skills/next-section-repo/`.

1. Read the route, the Figma URL and the repo from the trigger, and `--mobile <url>` (Case A). The `mobile` route (Case B) gives M's URL. Record `viewport: mobile` for M, otherwise `viewport: desktop`. Resolve the repo from `targets/repos.md`, or use the path the user gave (a worktree counts). Take the node id from the URL's `node-id`, written with `-`. Stop if a URL has no node id.
   - `resync <Folder> <mobile-url> <repo> --mobile` is a mobile pass on M: step 6m, then 04m in drift mode (the new overlay is diffed against the existing `bps.mobile` rules only), then 05m. It never runs desktop 04 drift on D.
   - `element <mobile-url> <repo> <file> --mobile` records `viewport: mobile` and `pair: none`, and runs as `element`.
2. Create `stages/01-export/output/<node-id>/`. From `skills/next-section-repo/`, run `python3 scripts/probe_repo.py --repo <repo> --out <workspace>/stages/01-export/output/<node-id>/profile.json`. Show its `warnings`. A mobile pass goes on at step 6m.
3. Run `$FIGMA --version` and `$FIGMA inspect '<url>' > stages/01-export/output/<node-id>/inspect.txt`. On `element`, write the export record now with the target file and go to step 8.
4. With `--mobile` (Case A), create `stages/01-export/output/<M>/` and preflight M: `$FIGMA inspect '<M url>' > stages/01-export/output/<M>/inspect.txt`, `$FIGMA render '<M url>' --out stages/01-export/output/<M>/figma.png --scale 1`, `$FIGMA export '<M url>' --dump stages/01-export/output/<M>/nodes.json`. No scaffold for M. D's record gets `pair: <M>`.
5. Pick the folder name. `sync` and `resync` use the folder the user named. `new` proposes the PascalCase layer name; stage 02 confirms it with you. The name has no `Server` and is not a global fragment name in the profile.
6. Run `$FIGMA render '<url>' --out stages/01-export/output/<D>/figma.png --scale 1` and `$FIGMA export '<url>' --out stages/01-export/output/<D>/preview.html`. When a pair is known, also `$FIGMA export '<url>' --dump stages/01-export/output/<D>/nodes.json`. Then scaffold: `$FIGMA export '<url>' --dist stages/01-export/output/<D>/scaffold --scaffold next-section --component <Folder> --repo-profile stages/01-export/output/<D>/profile.json --section-map stages/01-export/output/<D>/section-map.json [--font-map 'Family=export']`. The map stays outside the `--dist` folder. On a `font-unmatched` note, ask which `theme.fonts` export the family is (list the profile's fonts) and rerun with `--font-map`.
7. On exit 9 or 10, stop at the checkpoint.
8. Run the audit. Write `stages/01-export/output/<node-id>/export-record.md` with every `note:` line, `viewport`, `pair` and `section-map`, plus `baseline` and `class-map` on a mobile record (`shared/run-records.md`).
9. Continue on the route: `new` and `sync` load `../02-field-plan/CONTEXT.md`; `resync` and `element` load `../04-conform-bind/CONTEXT.md`. On `viewport: mobile`, load `../04-conform-bind/CONTEXT.md` in mobile mode (02 and 03 are skipped): `resync --mobile` in drift mode, `element --mobile` in element mode.

### Step 6m: mobile pass (`mobile`, `resync --mobile`, Case A)

D's record is the one M's `pair:` names (Case A), or the newest whose folder and repo match the trigger (`mobile`, `resync --mobile`). With no D record, ask for the desktop URL. Case B appends `pair: <M>` to D's record.

1. Run `$FIGMA --version`, `$FIGMA inspect '<M url>' > stages/01-export/output/<M>/inspect.txt`, `$FIGMA render '<M url>' --out stages/01-export/output/<M>/figma.png --scale 1` and `$FIGMA export '<M url>' --out stages/01-export/output/<M>/preview.html`. 05m Level 1 reads them.
2. If D's record has no `section-map.json`, rerun D's scaffold with D's record URL and flags (or the URL the user gave, after probing into `stages/01-export/output/<D>/`), never into the repo: `$FIGMA export '<D url>' --dist stages/01-export/output/<D>/scaffold --scaffold next-section --component <Folder> --repo-profile stages/01-export/output/<D>/profile.json --section-map stages/01-export/output/<D>/section-map.json`, plus D's `--font-map`.
3. Run `$FIGMA export '<M url>' --mobile-of stages/01-export/output/<D>/section-map.json --section-dir <app root>/<sectionsDir>/<Folder> --overlay-out stages/01-export/output/<M> --repo-profile stages/01-export/output/<M>/profile.json`. Add `--class-map stages/04-conform-bind/output/<D>/class-map.json` when it exists, and the same `--font-map` as D's record.
4. Exit 0: go to step 8. Exit 12 (`unmatched` or `target-missing` rows): stop at the checkpoint, then rerun step 3 with `--map stages/01-export/output/<M>/viewport-map.json` (`references/viewport-map.md`). Exit 11 (`new-content` rows): stop. Say the group needs a field and the route is `sync <Folder> <desktop-url> <repo> --mobile <mobile-url>`. Never add a field in a mobile pass.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 6 | A `font-unmatched` family and the theme's font exports | Which export to map it to |
| 7 | The paths from exit 10, or the children from exit 9 | Which layer to export |
| 6m | No D record for the folder | The desktop URL |
| 6m.4 | Exit 12: the `unmatched` and `target-missing` rows of `viewport-map.md` | Each row's target, status or touch. A `target-missing` row is usually a `class-map.json` entry |
| 6m.4 | Exit 11: the `new-content` rows | Run `sync ... --mobile` to add the field |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Profile | `profile.json` exists and is schemaVersion 1 |
| Staging only | Nothing was written under the repo |
| Scaffold | `scaffold/<Folder>/` holds the profile's scaffold files other than the `.gql`. M has no `scaffold/` |
| No URLs | No file under `scaffold/` contains `https://` |
| Record | The export record has the route, folder, figma-cli `--version` line, `viewport`, `pair`, `section-map` and every `note:` line |
| Section map | A desktop scaffold wrote `section-map.json` beside `scaffold/`, not inside it |
| Map (01m) | No `unmatched` or `target-missing` row is left without a user decision |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Export record | `output/<node-id>/export-record.md` | See `shared/run-records.md` |
| Profile, inspect, render, preview | `output/<node-id>/` | `profile.json`, `inspect.txt`, `figma.png`, `preview.html` |
| Scaffold, section map, dump | `output/<D>/` | `scaffold/<Folder>/`, `section-map.json`, `nodes.json` (pair known) |
| Mobile preflight (Case A) | `output/<M>/` | `inspect.txt`, `figma.png`, `nodes.json` |
| Viewport map and overlay (01m) | `output/<M>/` | `viewport-map.md`, `viewport-map.json`, `mobile-overlay.json`, `mobile-overlay.styled.txt` |
