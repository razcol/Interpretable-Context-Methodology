---
name: acf-section-fields
description: Reads React, Next.js, or HTML section files and audits them against the Jaecoo and luxury-trade WordPress ACF flexible layouts (field group `fields`, flexible field `flexible`). Use when adding or comparing ACF fields for those section components. The human adds the layout in the WordPress dashboard.
---

# ACF section fields

Use this for Jaecoo and luxury-trade sections. The Next apps do not contain ACF field groups. They read one flexible field over WPGraphQL: group `fields`, field `flexible`, layout type `FieldsFlexible<Folder>Layout`. Details and shared fragments are in [references/field-patterns.md](references/field-patterns.md).

In the figma-section-fields workspace, stage 02 writes `<Folder>.gql` and `field-report.md` in the section folder. The human adds the layout in the WordPress dashboard from that report. Follow `stages/02-section-graphql/CONTEXT.md` for that run.

## Process

1. **Pick the repo.** Use the project this run already named. In this workspace that path is in `targets/repos.md`. The two sites do not share a field database. If the files are a new design, still pass the repo they will be built in.
2. **Audit the files.** From this skill folder:

```bash
python3 scripts/audit_sections.py \
  --repo /path/to/code \
  --file path/to/component.js \
  --name FolderName
```

Add `--name FolderName` when the path is not already `components/Sections/<Folder>/`. One HTML file can hold several `<section data-section="FolderName">` blocks. Pass `--md-dir` only when a markdown audit file is wanted outside this workspace. This workspace reads the JSON on stdout and does not pass `--md-dir`.

3. **Read the report before trusting it.** `frontend_contract: found` means a `.gql` fragment exists, not that production has the layout. `inferred` fields are a guess from markup or props. `order` is never a field. A sibling warning means the other site's layout is different; do not merge them.
4. **Fields are added in the WordPress dashboard** for that environment. Edit the existing `fields` / `flexible` group. Add one layout whose Name is the folder name. Duplicate `layout`, button, and image fields from a layout that already uses the same fragments. Do not import or sync a field group.
5. **A new section still needs** `components/Sections/<Folder>/<Folder>.gql` on `FieldsFlexible<Folder>Layout`, using the shared fragments. Do not add a field group, PHP registration, or `acf-json` directory to the Next repo.

## Rules

- Add a layout to the existing flexible field. Do not create a new field group for a section.
- Do not change a subfield that is already on the layout.
- Image fields follow `MediaItem` (`node.mediaItemUrl`), not a URL return value. Buttons follow `ButtonItem`, not the ACF link field, unless the fragment already selects `url`, `title`, and `target`.
- Options pages and page-template groups (`contactUsTemplateFields` and similar) are not flexible layouts. Do not add them as layouts on `flexible`.
- The layout Name is the folder name. Do not snake_case it.

## Scripts

| Script | Effect |
| --- | --- |
| `scripts/audit_sections.py` | Reads the repo and the given files. Prints a JSON report. |
