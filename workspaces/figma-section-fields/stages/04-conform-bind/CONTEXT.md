# Stage 04: Conform and Bind

Put the staged scaffold into the repo and bind it to the fragment. On `resync`, apply only the design drift to the existing section. On `element`, restyle one existing control.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-export/output/<node-id>/export-record.md` | Full file | Route, repo, folder, target file, notes |
| Profile | `../01-export/output/<node-id>/profile.json` | Full file | Repo shape for the checker |
| Scaffold | `../01-export/output/<node-id>/scaffold/<Folder>/` | All files | The repo-shaped component |
| Inspect | `../01-export/output/<node-id>/inspect.txt` | Nodes of the target (`element`) | Figma values for the control |
| Fragment | `<app root>/<sectionsDir>/<Folder>/<Folder>.gql` | Full file | Fields to bind (`new`, `sync`) |
| Rules | `references/binding-rules.md` | The section for this route | How to bind, merge drift, edit a control |
| Repo skill | `../../skills/next-section-repo/SKILL.md` | `check_section.py` section | The audit |
| Checklist | `../../skills/next-section-repo/references/conformance-checklist.md` | Rows marked manual | What the checker cannot see |

## Process

1. Read the route from the export record and follow that section of `references/binding-rules.md`.
2. `new` and `sync`: copy the scaffold files into `<app root>/<sectionsDir>/<Folder>/` next to the `.gql`, keeping `field-report.md`. Then bind: in `Server<Folder>.js`, read each fragment field from props and pass the client what it renders; in `Client<Folder>.js`, replace each content prop with the bound value.
3. `resync`: diff the new scaffold against the existing section folder. Apply structure and style changes. Keep every binding, prop name, propTypes entry and hand-written logic that is not Figma output.
4. `element`: edit only the target file and its styles so the control matches the Figma values in `inspect.txt`, using theme tokens.
5. Show the binding table, or the drift list, or the control diff.
6. Run `check_section.py --repo <app root> --folder <Folder> --profile <profile.json>`. Fix every `fail` row, then rerun. Check the checklist rows marked manual.
7. Run the audit. Write `output/<node-id>/conform-record.md`.
8. Continue. Load `../05-verify/CONTEXT.md`.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 5 | Binding table, drift list, or control diff | Change a binding or skip a drift item |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Checker | `check_section.py` reports no `fail` (warnings listed in the record) |
| Fields | Every fragment field is rendered, or listed unused with a reason |
| Defaults | No Figma sample text is left as a default for a field the fragment provides |
| Images | No image file and no Figma URL in the folder |
| Resync | No binding, prop or propTypes entry from before the run was lost |
| Mount | The section is mounted only where the user already said |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Section | `<app root>/<sectionsDir>/<Folder>/` | Repo files bound to the fragment |
| Conform record | `output/<node-id>/conform-record.md` | Files changed, bindings or drift, checker result |
