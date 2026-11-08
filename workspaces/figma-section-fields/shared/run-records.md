# Run records

A run is one Figma node on one route. Its key is the node id with `:` written as `-` (`1404-7715`). Every stage writes into `stages/0N-*/output/<node-id>/`, so two runs on different sections never overwrite each other. A second run on the same node replaces that node's records.

A section with a mobile design has two runs: the desktop run D and the mobile run M, each in its own node folders. Their export records name each other with `pair:` lines. The mobile pass has three stages: 01m, 04m and 05m. It writes into the same stage folders as desktop, under M.

Output folders are git-ignored. Records are history for `status` and for the next stage of the same run. They are not templates: a stage never reads another run's records, except that the mobile pass reads its pair's records.

## Records

| Stage | Files | Holds |
|---|---|---|
| 01 | `stages/01-export/output/<D>/`: `export-record.md`, `profile.json`, `inspect.txt`, `figma.png`, `preview.html`, `scaffold/<Folder>/`, `section-map.json`, `nodes.json` (when a pair is known) | Route, Figma URL, node id, repo, app root, folder, figma-cli `--version` line, flags, every `note:` line, viewport, pair |
| 01m | `stages/01-export/output/<M>/`: `export-record.md`, `profile.json`, `inspect.txt`, `figma.png`, `preview.html`, `nodes.json` (dump), `section-map.json` (figma-cli's mobile row map, an artifact; the record's `section-map:` line never names it), `viewport-map.json`, `viewport-map.md` (edit surface), `mobile-overlay.json`, `mobile-overlay.styled.txt`. No `scaffold/` | The mobile record, the map with your edits, the overlay figma-cli emitted |
| 02 | `stages/02-field-plan/output/<D>/`: `field-plan.md`, `field-plan.json` | The plan you approved or are reviewing, the questions and your answers |
| 03 | `stages/03-fragment/output/<D>/`: `fragment-record.md` | The `.gql` path, `diff-group` result, `check-fragment` summary |
| 04 | `stages/04-conform-bind/output/<D>/`: `conform-record.md`, `class-map.json` (when it renames scaffold classes) | Files written or changed, the binding table, drift applied, `check_section` result. `class-map.json` maps each renamed scaffold class to its repo selector |
| 04m | `stages/04-conform-bind/output/<M>/`: `conform-record.md` (mobile) | The pair, the map rows applied, the touch paths, the icon decisions, the specificity notes, `check_section` result |
| 05 | `stages/05-verify/output/<D>/`: `verify-report.md`, `shots/`, `shots/baseline__<W>x<H>.png` | Level 1 diff ratio, Level 2 widths and overflow, PASS or FAIL. The baseline shots are the desktop regression reference for M |
| 05m | `stages/05-verify/output/<M>/`: `verify-report.md`, `shots/`, `shots/regression__*.png`, `shots/regression-diff.png` | Mobile widths, the 1279/1280 boundary, the desktop regression ratio, the tap check, PASS or FAIL |

`field-report.md` is not a record. It sits beside the component in the repo (stage 02) as a helper you delete later. It is not git-ignored.

## export-record.md

```markdown
# Export record <node-id>
- route: new | sync | resync | element | mobile
- viewport: desktop | mobile
- pair: <other node-id> | pending | none | out-of-scope
- figma: <url>
- node: <node-id>
- repo: <repo root>   app: <app root>
- folder: <Folder>    section path: <app root>/<sectionsDir>/<Folder>
- target file (element only): <path>
- section-map: <path> | none
- baseline (mobile only): stages/05-verify/output/<D>/shots/baseline__<W>x<H>.png | from-head <git sha>
- class-map (mobile only): <path> | none
- figma-cli: <output of --version>
- flags: <scaffold flags used>
- notes: <each note: line, or none>
```

- `section-map:` on a desktop record is `stages/01-export/output/<D>/section-map.json`, written by the scaffold with `--section-map`. On a mobile record it is still that desktop map, `stages/01-export/output/<D>/section-map.json`, the one 01m matched against. `stages/01-export/output/<M>/section-map.json` is figma-cli's mobile row map, an artifact that no record line names.
- `class-map:` on a mobile record is `stages/04-conform-bind/output/<D>/class-map.json` when desktop 04 renamed scaffold classes, otherwise `none`.

Later records start with the same `# <Stage> record <node-id>` line and list facts as bullets, then tables.

## Pair rules

- A desktop record from `new` or `sync` without `--mobile` gets `pair: pending`. With `--mobile` it gets `pair: <M>`, and M's preflight record gets `pair: <D>`.
- At the end of desktop 05 on a `pair: pending` record, the agent asks once: "Mobile design URL, or `mobile out of scope`?" The answer sets `pair:` to that URL's node id and starts the mobile pass, or sets it to `out-of-scope`.
- `pair: none` means no mobile pass is expected, as on an `element` run. A rerun on D keeps D's `pair:` line.
- `mobile` (Case B) writes `pair: <D>` in M's record and appends one `pair: <M>` line to D's record. This is the only edit a run makes to another node's record.

## How `status` works

List each `<node-id>` folder under `stages/01-export/output/`. For each, read `route`, `viewport`, `pair` and `folder` from its `export-record.md`. Mark every stage on that route COMPLETE when its record exists in `stages/0N-*/output/<node-id>/`, otherwise PENDING. A `new` run with a field plan and no fragment record is "02 waiting for you". A mobile run with a viewport map that still has `unmatched` or `target-missing` rows and no 04m record is "01m waiting for you". Say when the section folder named in the record no longer exists.

A run without a mobile pair:

```
Run <node-id> (<route>, <Folder>, <repo>)
  [01-export] --> [02-field-plan] --> [03-fragment] --> [04-conform-bind] --> [05-verify]
     STATUS          STATUS              STATUS            STATUS              STATUS
```

When a desktop record D and a mobile record M name each other in `pair:` lines, show them as one block:

```
Section ImageGrid (ora, /home/dev/ora-next/.worktrees/OND-7)
  desktop 3919-20727 (sync)   [01] --> [02] --> [03] --> [04] --> [05]   STATUS ...
  mobile  1482-11000 (mobile) [01m] --> [04m] --> [05m]                  STATUS ...
```

The mobile stages are COMPLETE when these exist: 01m `stages/01-export/output/<M>/mobile-overlay.json`, 04m `stages/04-conform-bind/output/<M>/conform-record.md`, 05m `stages/05-verify/output/<M>/verify-report.md`. A desktop record with `pair: pending` shows `mobile pending` under its line. One with `pair: out-of-scope` shows `mobile out of scope`.
