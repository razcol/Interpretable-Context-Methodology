# GraphQL stage notes

Field shapes come from the live schema of the repo in the export record. Read `_core/skills/wp-graphql/SKILL.md` and run its commands. Do not write a GraphQL query. Do not read `skills/acf-section-fields/references/field-patterns.md` for this stage. That file describes Jaecoo and luxury-trade, and those shapes are not this repo.

## Where the fragment goes

Write `<export-dir>/<Folder>/<Folder>.gql` next to the component. The stage 01 export record names that folder.

The fragment name is the folder name. The `on` type is:

- `layoutType` from `section`, when `onFlexibleUnion` is true.
- `FieldsFlexible<Folder>Layout` when the section is not on the flexible union yet. Page templates read `fields.flexible`. A standalone field group does not enter that list. The selection set is still the group's tree, so the same fields can move onto a layout of this name later.

## What to run

From the wp-graphql skill folder, with `--repo` set to the repo in the export record:

```bash
python3 scripts/wp_graphql.py patterns --repo <repo>
python3 scripts/wp_graphql.py section <Folder> --repo <repo>
```

Add `--refresh` only when the user just changed ACF. After the file is written:

```bash
python3 scripts/wp_graphql.py check-fragment <export-dir>/<Folder>/<Folder>.gql --repo <repo>
```

`summary` is the result. Read `tree` when writing the selection, because `summary` lists only the top level. `patterns.examples` names one existing section per shape. Open that section's `.gql` and copy its spread. Do not invent a second spread for the same shape.

## When the section is already in the schema

`groupType` or `layoutType` is set. The selection set copies `tree`:

- Use each node's `name` as saved. `cardslist` stays `cardslist` when that is the live name.
- A node whose `shape` is set becomes that shape's spread, not a hand-written field list.

| `shape` | Spread this repo already uses |
|---|---|
| `responsiveFull` | `...BackgroundFields` |
| `responsiveMedia` | `...ResponsiveMediaItem` |
| `mediaItem` | `...MediaItem`. When `imageOn` is `edge`, the selection is `node { ...MediaItem }`. |
| `button` | `...Button` |
| `spacing` | `...Layout` |

If the example section's `.gql` uses a different spread for that shape, use the example. One field, one shape. A rest picture and a hover picture are two fields of the same shape. They are not `desktop` and `mobile` inside one field.

`similarLayout` (also returned as `cloneFrom`) is another layout with similar field names. It is not an ACF clone. Ignore it when `fragment.missingOnSchema` is not empty. The live `tree` is the source in that case. A field label `clone of SomeType` is the reused GraphQL type; copy that type's spread, not the other layout's whole selection.

## When the section is not in the schema

Compose the selection from the component's distinct content and from `patterns`. Shape the fields the way this repo already shapes them.

- Heading, second line, and intro paragraph go in one group named `header`. The group's name and a child's name must differ. A group named `title` with a child named `title` is the same field twice.
- A repeated card is a repeater. Use the repeater name from the closest example, such as `cardsList`, unless the design is a single block.
- A picture that can be an image or a video is `responsiveFull`. A desktop and mobile pair of one picture is `responsiveMedia`. A single image with no pair and no video branch is `mediaItem`. Pick the shape `patterns.examples` shows for that kind of picture, then use a second field of the same shape for a hover picture.
- One button is a group. The button clone sits inside the group (`button { ...Button }`). A seamless clone pastes `text`, `variant`, and the link groups onto the section and collides with the next button. Several buttons are a repeater, using the repeater name from the example section (`buttonsList` or `buttonFields` as that file writes it).
- A disclaimer line is one text field. Name it `disclaimer` unless an example layout already uses another name for that line.
- Add `spacing` only when `counts.spacing` is greater than 0.

## Check the file

`check-fragment` compares the file with the layout type, or with the field group when that layout type is absent.

- Fix any absent field that belongs to this section.
- Leave a missing `mediaItemId` that appears only under `...MediaItem` or `...BackgroundFields`. That leaf is inside the shared media fragment. This schema's `MediaItem` type does not have `mediaItemId`. Do not add it, and do not stop using the shared spread because of it.
- Fix `node` selected on `MediaItem`, and a `...MediaItem` spread placed directly on a connection edge. The edge's image is `node`, then the `MediaItem` fields.
- A selected field whose shape differs from the live node is rewritten to the live shape.

## Field report

`<export-dir>/<Folder>/field-report.md` lists the fields in the `.gql` just written. It does not live under this stage `output/`.

The steps say:

- Edit the field group whose GraphQL field name is `fields`. Do not create a group.
- Add one layout on `flexible`. The layout Name is the folder name.
- For each shaped field, name the example section from `patterns.examples` and tell the human to duplicate that field. A button clone is wrapped in a group or a repeater. It is not seamless.
- Copy text fields and repeaters by the names in the `.gql`.
- When `section` already returned this tree on a standalone group, say that the group exists and that these same fields still need to become that layout before a page can place the section.
- Save the group. Other layouts stay as they are.

## What this stage must not do

- Do not add a field group, PHP registration, or `acf-json` to the Next repo.
- Do not import or merge a layout from another site.
- Do not write the fragment from string literals in the Figma export when `section` or `patterns` already has a shape for that content.
- Do not write an audit markdown file or `field-report.md` under this stage `output/`.
