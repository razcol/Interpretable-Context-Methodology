# GraphQL stage notes

Read `skills/acf-section-fields/SKILL.md` in full before writing a fragment. When writing the fragment, also read `skills/acf-section-fields/references/field-patterns.md` for shared fragments and the layout type.

## Where the fragment goes

Write `<export-dir>/<Folder>/<Folder>.gql` next to the component. The stage 01 export record names that folder.

```
fragment <Folder> on FieldsFlexible<Folder>Layout {
```

Use the folder's PascalCase name. Take shared fragment spreads from the skill. Do not invent a second layout type.

## What this stage must not do

- Do not add a field group, PHP registration, or `acf-json` to the Next repo.
- Do not import or merge a layout from the other site. The two sites do not share a field database.
- Do not use a snake_case layout name. The layout Name is the folder name.
- Do not write an audit markdown file or `field-report.md` under this stage `output/`.

## Audit script

From the workspace root:

```
python3 skills/acf-section-fields/scripts/audit_sections.py \
  --repo <chosen-project> \
  --file <component.js> \
  --name <Folder>
```

Read the JSON on stdout. `inferred` fields are a guess. `order` is not a field. Do not pass `--md-dir`. The human adds the layout in the WordPress dashboard.

## When the audit infers nothing

This is the usual Figma export. `figma-cli` writes a styled shell: Hebrew and English copy as string literals, images as `url(./assets/...)` in the styled file, and a button as a labeled box. The component takes no props, so the audit returns an empty fragment. That empty snippet is not the proposal.

Read `INTERIOR.js` (or whichever component the export record names) and `Styled<Name>.js`. Propose one field per distinct piece of content:

- One text or wysiwyg field per heading and paragraph.
- A repeater when the same card (image plus caption) repeats. Each card image is a `MediaItem`, not one `ResponsiveMediaItem`, unless the design is a desktop/mobile pair of the same picture.
- A button group whose name and spread already exist in this repo (`buttonsList { ...Button }` on ora-next).
- `...Layout` for section spacing.

Write the `.gql` in the same run. Show the table in the reply. The `.gql` is the frontend surface. It does not mean the WordPress layout exists yet. Then write the field report in that same folder and continue to stage 03.

## Dashboard steps

This stage does not configure WordPress. `<export-dir>/<Folder>/field-report.md` is the checklist the human follows in that site's admin. It ships in the section folder with `index.js`, `<Folder>.js`, `Styled<Folder>.js`, and `<Folder>.gql`. Do not tell the human to import or sync a field group.

Write the steps for the confirmed fragment only. Use the field names in the `.gql`. For each shared spread, name an existing layout in this repo that already uses it, and tell the human to duplicate that field onto the new layout. Duplicating keeps the GraphQL shape the other sections already use. Rebuilding a button or an image field by hand is how the fragment breaks.

The steps always say:

- Edit the field group whose GraphQL field name is already `fields`. Do not create a group.
- Add one layout on the flexible field `flexible`. The layout Name is the folder name, matching the fragment type `FieldsFlexible<Folder>Layout`.
- Leave Show in GraphQL as it already is on that group. Other sections such as `ModelCtaBanner` already resolve through it.
- Duplicate `layout` from a layout that spreads `...Layout`.
- Duplicate a button repeater or group from a layout that spreads the same button fragment this `.gql` uses.
- Duplicate an image field from a layout that spreads `...MediaItem` or `...ResponsiveMediaItem`, matching which of those this `.gql` uses. The return format stays Image Array.
- Add plain text, wysiwyg, and new repeaters by the names in the `.gql`.
- Save the group. Other layouts stay as they are.
- In the site's GraphQL IDE, confirm the new type is `FieldsFlexible<Folder>Layout`, the same pattern as `FieldsFlexibleModelCtaBannerLayout`.
