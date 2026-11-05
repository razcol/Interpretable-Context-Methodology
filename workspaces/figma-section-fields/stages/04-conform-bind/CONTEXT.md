# Stage 04: Conform and Bind

Put the staged scaffold into the repo and bind it to the fragment. On `resync`, apply only the design drift to the existing section. On `element`, restyle one existing control. On a mobile pass, nest the mobile overlay into the built section.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-export/output/<node-id>/export-record.md` | Full file | Route, viewport, pair, repo, folder, target file, notes |
| Profile | `../01-export/output/<node-id>/profile.json` | Full file | Repo shape for the checker |
| Scaffold | `../01-export/output/<node-id>/scaffold/<Folder>/` | All files | The repo-shaped component (desktop) |
| Inspect | `../01-export/output/<node-id>/inspect.txt` | Nodes of the target (`element`) | Figma values for the control |
| Fragment | `<app root>/<sectionsDir>/<Folder>/<Folder>.gql` | Full file | Fields to bind (`new`, `sync`) |
| Mobile map | `../01-export/output/<M>/viewport-map.md` and `.json` | Full file, with your edits (mobile) | Which repo selector each mobile row targets |
| Overlay | `../01-export/output/<M>/mobile-overlay.json` and `mobile-overlay.styled.txt` | Full file (mobile) | Deltas, hide, order, decor, touch per selector |
| Rules | `references/binding-rules.md` | The section for this route, or "mobile: overlay" | How to bind, merge drift, edit a control, nest the overlay |
| Mobile rules | `../../skills/next-section-repo/references/mobile-patterns.md` | Full file (mobile) | How a mobile rule is written |
| Repo skill | `../../skills/next-section-repo/SKILL.md` | `check_section.py` section | The audit |
| Checklist | `../../skills/next-section-repo/references/conformance-checklist.md` | Rows marked manual | What the checker cannot see |

## Process

1. Read the route and `viewport` from the export record and follow that section of `references/binding-rules.md`. `viewport: mobile` switches to mobile overlay mode: follow "mobile: overlay" instead of steps 2 to 4, load the mobile rows above, and do not load the scaffold or the fragment.
   - `resync --mobile`: mobile mode in drift mode. Diff the new overlay against the existing `bps.mobile` rules only; never run desktop drift (step 3) on D.
   - `element --mobile`: follow "element" (step 4), not mobile mode. Change only rules inside `bps.mobile` blocks of the target file.
2. `new` and `sync`: copy the scaffold files into `<app root>/<sectionsDir>/<Folder>/` next to the `.gql`, keeping `field-report.md`. Then bind: in `Server<Folder>.js`, read each fragment field from props and pass the client what it renders; in `Client<Folder>.js`, replace each content prop with the bound value. When you rename or restructure scaffold classes, write `output/<node-id>/class-map.json`.
3. `resync`: diff the new scaffold against the existing section folder. Apply structure and style changes. Keep every binding, prop name, propTypes entry and hand-written logic that is not Figma output, and every rule from a mobile pass.
4. `element`: edit only the target file and its styles so the control matches the Figma values in `inspect.txt`, using theme tokens.
5. Show the binding table, or the drift list, or the control diff. In mobile mode: the drift list per map row, the touch rows that need a decision, and the icon candidates.
6. From `skills/next-section-repo/`, run `python3 scripts/check_section.py --repo <app root> --folder <Folder> --profile /home/dev/ai-system/workspaces/figma-section-fields/stages/01-export/output/<node-id>/profile.json`, plus `--mobile-pass` in mobile mode. Fix every `fail` row (in mobile mode, only on files the pass may change; see the mobile Checker audit), then rerun. Check the checklist rows marked manual.
7. Run the audit (mobile mode adds the audit in "mobile: overlay"). Write `output/<node-id>/conform-record.md`.
8. Continue. Load `../05-verify/CONTEXT.md`.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 5 | Binding table, drift list, or control diff | Change a binding or skip a drift item |
| 5 (mobile) | Drift list per map row, `touch.source=checkpoint` rows, icon candidates per decor row | Skip a row; tap toggle, always shown or hidden; which icon, or a new SVG |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Checker | `check_section.py` reports no `fail` (warnings listed in the record) |
| Fields | Every fragment field is rendered, or listed unused with a reason |
| Defaults | No Figma sample text is left as a default for a field the fragment provides |
| Images | No image file and no Figma URL in the folder |
| Resync | No binding, prop or propTypes entry, and no mobile-pass rule, from before the run was lost |
| Class map | Every scaffold class this pass renamed is in `class-map.json` |
| Mount | The section is mounted only where the user already said |
| Mobile | The "mobile: overlay" audit passes (mobile mode only, replaces Fields and Defaults) |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Section | `<app root>/<sectionsDir>/<Folder>/` | Repo files bound to the fragment, or with the mobile overlay nested |
| Conform record | `output/<node-id>/conform-record.md` | Files changed, bindings or drift, checker result. Mobile: see `binding-rules.md` "Record" |
| Class map | `output/<D>/class-map.json` | `{ "<scaffold class>": "<repo selector>" }`, only when classes were renamed |
| Before copies | `output/<M>/before/` | `Styled<Folder>.js` and `Client<Folder>.js` before the mobile pass |
