# Stage 02: Section GraphQL

Write the ACF flexible-field fragment for the exported section.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-figma-export/output/export-record.md` | Full file | Component name and folder |
| Component | Paths in the export record | `index.js`, `<Name>.js`, `Styled<Name>.js` | Infer fields from the JSX |
| Skill | `../../skills/acf-section-fields/SKILL.md` | Full file | How to audit and write the fragment |
| Patterns | `../../skills/acf-section-fields/references/field-patterns.md` | Shared fragments and layout type | Shape to use while writing the `.gql` |
| Stage notes | `references/graphql-stage.md` | Full file | Where the file goes, and what to skip |

## Process

1. Read the export record and the component files.
2. Read `SKILL.md` in full. When writing the fragment, read `field-patterns.md` for shared fragments and the layout type.
3. From the workspace root, run `python3 skills/acf-section-fields/scripts/audit_sections.py` with `--repo` set to the chosen project, `--file` set to the component js, and `--name` set to the folder. Do not pass `--md-dir`. Read the JSON on stdout.
4. An empty field list is the usual Figma export: the component has string literals and CSS asset urls, not props or HTML tags. In that case propose fields from those literals and urls, using this repo's shared fragments. See `references/graphql-stage.md`.
5. Write `<export-dir>/<Folder>/<Folder>.gql` in this same run from that proposal. Show the field list in the reply. The human can edit the file afterward. Do not wait for another message before writing it.
6. The fragment type is `fragment <Folder> on FieldsFlexible<Folder>Layout`. WordPress can lag behind this file.
7. Do not add a field group to the Next repo. Do not merge the other site's layout.
8. Write `<export-dir>/<Folder>/field-report.md` with dashboard steps for this section, following `references/graphql-stage.md`. It sits in the same folder as the component and the `.gql`. The steps add one layout on the existing `fields` / `flexible` group. Do not write this report, or an audit markdown file, under this stage `output/`. Do not import or sync a field group.
9. Continue this run. Load `../03-field-migration/CONTEXT.md` and follow it. The fragment to bind is the `.gql` just written. Do not end the run after the field report.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 5 | The written fragment and the field list | Edit the `.gql` if a name should change |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Confirmed fields | The `.gql` file uses the names and types the human confirmed |
| Layout type | The fragment is on `FieldsFlexible<Folder>Layout` |
| One site | The fragment was built from the repo named in the export record |
| Report | `<export-dir>/<Folder>/field-report.md` names the `.gql` beside it and the dashboard steps for this section |
| No shared report | This stage `output/` has no `field-report.md` and no `<Folder>.md` |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Fragment | `<export-dir>/<Folder>/<Folder>.gql` | `fragment <Folder> on FieldsFlexible<Folder>Layout` |
| Field report | `<export-dir>/<Folder>/field-report.md` | Dashboard steps that make this `.gql` resolve |

This stage `output/` stays empty apart from `.gitkeep`. The report lives in the section folder so a parallel run on another section cannot overwrite it.
