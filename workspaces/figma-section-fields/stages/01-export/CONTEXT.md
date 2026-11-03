# Stage 01: Export

Read the repo's structure, read the Figma layer, and write the repo-shaped scaffold into this run's staging folder. Nothing is written into the repo here.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Run | The trigger message | Route, Figma URL, repo, folder (`sync`, `resync`), target file (`element`) | What this run is |
| Targets | `../../targets/repos.md` | Full file | Repo root and default repo |
| Repo skill | `../../skills/next-section-repo/SKILL.md` | `probe_repo.py` section | The repo profile |
| Setup | `../../shared/figma-cli-setup.md` | Full file | How to call figma-cli and load the token |
| Contract | `../../shared/export-contract.md` | Full file | Commands, notes and exit codes |
| Records | `../../shared/run-records.md` | `export-record.md` section | Record format |

## Process

1. Read the route, the Figma URL and the repo from the trigger. Resolve the repo from `targets/repos.md`, or use the path the user gave (a worktree counts). Take the node id from the URL's `node-id`, written with `-`. Stop if the URL has no node id.
2. Create `output/<node-id>/`. Run `probe_repo.py --repo <repo> --out output/<node-id>/profile.json`. Show its `warnings`.
3. Run `$FIGMA --version` and `$FIGMA inspect '<url>' > output/<node-id>/inspect.txt`. On `element`, write the export record now with the target file and go to step 8.
4. Pick the folder name. `sync` and `resync` use the folder the user named. `new` proposes the PascalCase layer name; stage 02 confirms it with you. The name has no `Server` and is not a global fragment name in the profile.
5. Run `$FIGMA render '<url>' --out output/<node-id>/figma.png --scale 1` and `$FIGMA export '<url>' --out output/<node-id>/preview.html`.
6. Run the scaffold export into `output/<node-id>/scaffold/` with `--component <Folder> --repo-profile output/<node-id>/profile.json`. On a `font-unmatched` note, ask which `theme.fonts` export the family is (list the profile's fonts) and rerun with `--font-map`.
7. On exit 9 or 10, stop at the checkpoint.
8. Run the audit. Write `output/<node-id>/export-record.md` with every `note:` line.
9. Continue on the route: `new` and `sync` load `../02-field-plan/CONTEXT.md`; `resync` and `element` load `../04-conform-bind/CONTEXT.md`.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 6 | A `font-unmatched` family and the theme's font exports | Which export to map it to |
| 7 | The paths from exit 10, or the children from exit 9 | Which layer to export |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Profile | `profile.json` exists and is schemaVersion 1 |
| Staging only | Nothing was written under the repo |
| Scaffold | `scaffold/<Folder>/` holds the profile's scaffold files other than the `.gql` |
| No URLs | No file under `scaffold/` contains `https://` |
| Record | The export record has the route, folder, figma-cli `--version` line and every `note:` line |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Export record | `output/<node-id>/export-record.md` | See `shared/run-records.md` |
| Profile, inspect, render, preview | `output/<node-id>/` | `profile.json`, `inspect.txt`, `figma.png`, `preview.html` |
| Scaffold | `output/<node-id>/scaffold/<Folder>/` | figma-cli `--scaffold next-section` output |
