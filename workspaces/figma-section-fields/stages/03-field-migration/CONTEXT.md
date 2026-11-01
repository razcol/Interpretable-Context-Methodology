# Stage 03: Field Migration

Bind fragment fields to the exported component.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-figma-export/output/export-record.md` | Full file | Component folder |
| Fragment | `<export-dir>/<Folder>/<Folder>.gql` | Full file | Fields to bind |
| Component | Files beside the `.gql` path | `index.js`, `<Folder>.js`, `Styled<Folder>.js` | JSX to edit |
| Rules | `references/migration-rules.md` | Full file | Binding rules |

## Process

1. Read the `.gql` file and the component js.
2. Plan a binding from each fragment field to the JSX: text nodes, images, and buttons.
3. Show the binding table in the reply and apply it in this same run. Do not wait for another message before editing.
4. Edit the component so content comes from those props. Leave the Styled file as the visual shell. Keep `index.js` as the default export.
5. `order` is not a field. Bind each selected field in the shape the `.gql` writes. A spread is that object. Do not replace it with a single image URL or a flat button.
6. If the user already gave a render location, wire the component only there and record the path. If they did not, stop. Do not ask where to render.
7. Run the audit. Write `output/migration-record.md` listing files changed and the field bindings.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 3 | Binding table from each fragment field to JSX | Edit a binding in the component if it should change |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Fields | Every fragment field is read by the component, or listed unused with a reason |
| Styled file | `Styled<Name>.js` still exists |
| Field group | No new field group was added |
| Mount | A render path appears only when the user already gave one |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Migration record | `output/migration-record.md` | Files changed and field bindings |
| Component | Files under the export folder | Props wired to the fragment |
