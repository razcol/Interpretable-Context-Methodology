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
4. Run `check-fragment` on that file. When `fragment.onExists` is false and `fragment.comparedTo` is null, the command did not compare the selection to a type. `missingOnSchema` and `shapeMismatches` are empty because there was no type, and `Every fragment field exists on the compared type.` is not a match. Do not rewrite the fragment from that run. Do not tell the human the section is configured or that the schema matches. When `missingOnSchema` or `shapeMismatches` is non-empty, or `comparedTo` is set to a group, fix a selected field the compared type does not have. A missing `mediaItemId` that comes only from the shared `MediaItem` fragment stays as it is. `node` selected on `MediaItem`, or `...MediaItem` placed on a connection edge, is a real failure: select `node`, then the `MediaItem` fields.
5. Write `<export-dir>/<Folder>/field-report.md` for the fragment just written, following the branch in `references/graphql-stage.md`. The first dashboard step matches the command keys. Both `section.layoutType` and `section.groupType` null means the first step creates the section group titled `section: <graphqlName>`, with GraphQL Field Name `<graphqlName>`. `<graphqlName>` is the folder name with only the first character lowercased. That step does not create the `fields` group. `section.groupType` set and `onFlexibleUnion` false means the first step opens that group by GraphQL Field Name and does not create it. `onFlexibleUnion` true means the first step opens the existing `fields` group and expands the layout. A set `patterns.flexibleField` means the report opens that `fields` group to add the layout and does not add a flexible field. `patterns.flexible` null does not by itself mean the `fields` group is absent. `flexible.union` may be an interface, and the key name stays `union`. Each field block names Field Label, Field Name, Field Type, and GraphQL Field Name. Do not write this report under this stage `output/`.
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
| Check | Either `fragment.comparedTo` is set and `check-fragment` reports no absent section fields and no shape mismatches, or `fragment.onExists` is false and `fragment.comparedTo` is null and the field report describes the fragment as unresolved. `mediaItemId` under a shared media spread does not fail this check. `node` on `MediaItem` does. `Every fragment field exists on the compared type.` is not a pass when nothing was compared |
| One site | The commands used the repo named in the export record |
| Report | `<export-dir>/<Folder>/field-report.md` names the `.gql` beside it, and its first dashboard step matches the keys. Both types null means the first step creates the section group titled `section: <graphqlName>` with that GraphQL Field Name, and does not create the `fields` group. `groupType` set and `onFlexibleUnion` false means the first step opens that group by GraphQL Field Name. `onFlexibleUnion` true means the first step opens the existing `fields` group and expands the layout. A set `patterns.flexibleField` means the report does not add a flexible field. A field block that omits Field Label, Field Name, Field Type, or GraphQL Field Name fails this check |
| No shared report | This stage `output/` has no `field-report.md` and no `<Folder>.md` |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Fragment | `<export-dir>/<Folder>/<Folder>.gql` | Selection from the live tree, or from `patterns` when the section is new |
| Field report | `<export-dir>/<Folder>/field-report.md` | Steps that make this `.gql` resolve |

This stage `output/` stays empty apart from `.gitkeep`. The report lives in the section folder so a parallel run on another section cannot overwrite it.
