# Stage 02: Section GraphQL

Write the `.gql` fragment for the exported section from the live WordPress schema.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-figma-export/output/export-record.md` | Full file | Component name, folder, and repo |
| Component | Paths in the export record | `index.js`, `<Name>.js`, `Styled<Name>.js` | Which content pieces the design has |
| WP GraphQL | `../../../../_core/skills/wp-graphql/SKILL.md` | Full file | Commands that read this repo's schema |
| Stage notes | `references/graphql-stage.md` | Full file | How those results become the `.gql` |

## Process

1. Read the export record and the component files. List the distinct content pieces: headings, cards, pictures, buttons, disclaimer.
2. Read the wp-graphql skill. From that skill folder, run `patterns` and `section <Folder>` with `--repo` set to the repo in the export record. Use `--refresh` only when the user just changed ACF.
3. Write `<export-dir>/<Folder>/<Folder>.gql` in this same run, following `references/graphql-stage.md`. Show the field list in the reply. The human can edit the file afterward. Do not wait for another message before writing it.
4. Run `check-fragment` on that file. Fix a selected field the compared type does not have. A missing `mediaItemId` that comes only from the shared `MediaItem` fragment stays as it is. `node` selected on `MediaItem`, or `...MediaItem` placed on a connection edge, is a real failure: select `node`, then the `MediaItem` fields.
5. Write `<export-dir>/<Folder>/field-report.md` for the fragment just written, following `references/graphql-stage.md`. Do not write this report under this stage `output/`.
6. Continue this run. Load `../03-field-migration/CONTEXT.md` and follow it. The fragment to bind is the `.gql` just written. Do not end the run after the field report.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 3 | The written fragment and the field list | Edit the `.gql` if a name should change |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Live tree | When `section` returns a type, every top-level field in `tree` is selected under the same name |
| Layout type | The fragment is on `layoutType` when `onFlexibleUnion` is true, otherwise on `FieldsFlexible<Folder>Layout` |
| Check | `check-fragment` reports no absent section fields and no shape mismatches. `mediaItemId` under a shared media spread does not fail this check. `node` on `MediaItem` does |
| One site | The commands used the repo named in the export record |
| Report | `<export-dir>/<Folder>/field-report.md` names the `.gql` beside it |
| No shared report | This stage `output/` has no `field-report.md` and no `<Folder>.md` |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Fragment | `<export-dir>/<Folder>/<Folder>.gql` | Selection from the live tree, or from `patterns` when the section is new |
| Field report | `<export-dir>/<Folder>/field-report.md` | Steps that make this `.gql` resolve |

This stage `output/` stays empty apart from `.gitkeep`. The report lives in the section folder so a parallel run on another section cannot overwrite it.
