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

`summary` is the result. Read `tree` when writing the selection, because `summary` lists only the top level. Branch the field report on `patterns.flexibleField`, `patterns.flexible`, `section.layoutType`, `section.groupType`, and `section.onFlexibleUnion`. Do not branch on a `summary` sentence. `flexible.union` is the GraphQL type that lists the layouts. On this kind of site that type is the interface `FieldsFlexible_Layout`, not a union. The JSON key stays `union` either way. `patterns.flexible` null means that layout list has fewer than two members. It does not mean the `fields` group is absent, and it does not mean a section group is absent.

`patterns.examples` is an object keyed by shape. Empty means `{}`. A missing shape is an omitted key, not a section named in another file. When the key for that shape is present, name that section in the field block and clone the same source group it uses. Do not invent a second spread for the same shape. When the key is absent, use the spread in the shape table in this file. Do not open another section's `.gql`.

`core.config.js`, page templates, and any `.gql` other than the example `patterns.examples` named are the Next app's expected path. They are not evidence that the WordPress group or the flexible field exists. If they disagree with `patterns.flexibleField`, `section.layoutType`, and `section.groupType`, the command JSON wins. A set `flexibleField` means the shared `fields` group and its `flexible` field are already there. Do not tell the human to create that group, and do not rename it. A missing section is a different group, titled `section: <graphqlName>`. Creating that section group is not creating the `fields` group.

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

When `patterns.examples` has that shape's key and the example section's `.gql` uses a different spread, use the example. When the key is absent, use the table. One field, one shape. A rest picture and a hover picture are two fields of the same shape. They are not `desktop` and `mobile` inside one field.

`similarLayout` (also returned as `cloneFrom`) is another layout with similar field names. It is not an ACF clone. Ignore it when `fragment.missingOnSchema` is not empty. The live `tree` is the source in that case. A field label `clone of SomeType` is the reused GraphQL type; copy that type's spread, not the other layout's whole selection.

## When the section is not in the schema

Compose the selection from the component's distinct content and from `patterns`. Shape the fields the way this repo already shapes them.

- Heading, second line, and intro paragraph go in one group named `header`. The group's name and a child's name must differ. A group named `title` with a child named `title` is the same field twice.
- A repeated card is a repeater. When `patterns.examples` names that section, use the repeater name from that example, such as `cardsList`, unless the design is a single block. When it does not, still use a repeater and do not cite another section's file.
- A picture that can be an image or a video is `responsiveFull`. A desktop and mobile pair of one picture is `responsiveMedia`. A single image with no pair and no video branch is `mediaItem`. When `patterns.examples` has a key for that kind of picture, use the shape that example shows, then use a second field of the same shape for a hover picture. When that key is absent, use the shape table in this file. Do not copy the spread from a section `patterns.examples` did not return.
- One button is a group. Inside that group, one Clone field points at the existing button group (`button { ...Button }`). Display is Seamless and prefix is off, so the cloned names stay `text` and `variant` inside the wrapper and do not land on the section itself. Several buttons are a repeater, and the Clone sits on the row. When `patterns.examples` names that section, use the repeater name that file writes (`buttonsList` or `buttonFields`). When it does not, still use a repeater and do not cite another section's file. Do not add the button group as its own flexible layout.
- A disclaimer line is one text field. Name it `disclaimer` unless `patterns.examples` names a layout that already uses another name for that line.
- Add `spacing` only when `counts.spacing` is greater than 0.

## Check the file

`check-fragment` compares the file with the layout type, or with the field group when that layout type is absent.

When `fragment.onExists` is false and `fragment.comparedTo` is null, the command did not compare the selection to a type. `missingOnSchema` and `shapeMismatches` are empty because there was no type. The summary line `Every fragment field exists on the compared type.` is not a match. Do not rewrite the fragment from that run. Do not tell the human the section is configured or that the schema matches. The field report says the fragment cannot resolve until this layout exists. When both `section.layoutType` and `section.groupType` are null, that report creates the section group. When `patterns.flexibleField` is set, it opens the existing `fields` group only to add the layout. It does not create that group.

A real mismatch is still fixed. That is `missingOnSchema` or `shapeMismatches` non-empty, or `comparedTo` set to a group:

- Fix any absent field that belongs to this section.
- Leave a missing `mediaItemId` that appears only under `...MediaItem` or `...BackgroundFields`. That leaf is inside the shared media fragment. This schema's `MediaItem` type does not have `mediaItemId`. Do not add it, and do not stop using the shared spread because of it.
- Fix `node` selected on `MediaItem`, and a `...MediaItem` spread placed directly on a connection edge. The edge's image is `node`, then the `MediaItem` fields.
- A selected field whose shape differs from the live node is rewritten to the live shape.

## Field report

`<export-dir>/<Folder>/field-report.md` is the click list for the `.gql` just written. It does not live under this stage `output/`.

A section is its own ACF field group. The shared `fields` group is the parent that already holds `flexible`. Do not create the `fields` group. Do not add a second Flexible Content field. Do not rename the `fields` group. Its list title is not in the schema.

`<graphqlName>` is the folder name with only the first character lowercased. `Layer01HIGHLIGHTS` becomes `layer01HIGHLIGHTS`. That string is a GraphQL name: a letter first, then letters and digits. It is not a label with spaces.

- Section group title, the list label: `section: <graphqlName>`.
- Section group GraphQL Field Name: `<graphqlName>`. Same string. Show in GraphQL: Yes.
- Layout Name inside `flexible`: the folder name, exact case. `Layer01HIGHLIGHTS` stays `Layer01HIGHLIGHTS`. The fragment stays `on FieldsFlexible<Folder>Layout`. Do not snake_case either string.

When `flexibleField.parentField` is `enFields`, write `enFields` and `enFlexible` in every place this section says `fields` and `flexible`, and the layout type is `EnFieldsEnFlexible<Folder>Layout`. Otherwise the parent GraphQL field name is `fields`, the flexible field name is `flexible`, and the layout type is `FieldsFlexible<Folder>Layout`.

The WordPress list title is not readable from GraphQL. Match a group by GraphQL Field Name. Say that in the report when the group already exists.

Do not shorten a field to one line such as `breadcrumb — text`. Do not write "add the fields from the `.gql`". Every field in the fragment gets the block below, in selection order, on the section group. A nested field is indented under its parent. It is not a sibling of that parent.

Field Label is the field name with a space before each capital and the first letter capitalized. `cardsList` becomes `Cards List`. `hoverImage` becomes `Hover Image`. `breadcrumb` becomes `Breadcrumb`. Field Name and GraphQL Field Name stay the fragment identifier. After the label is typed, overwrite Field Name when ACF generated `cards_list` or any slug other than the fragment name.

### Flexible parent, when `flexibleField` is set

Print this when the report adds or opens a layout. Do not click Add New for this group. Do not add a Flexible Content field. Do not change its location rules.

1. In WordPress admin, open Custom Fields, then Field Groups.
2. Open the group whose GraphQL Field Name is `fields`. The title in the list is not that name. Do not match it by the section folder name. `fields` is what pages query as `Page.fields`.
3. Scroll to the existing field whose Field Name is `flexible`. Confirm Field Type is already Flexible Content. Expand that field.

When `onFlexibleUnion` is true, the next step is: expand the layout whose Layout Name is the folder name. Do not add a second layout. Do not add another Clone of the section group.

When `flexibleField` is null, do not invent the `fields` group. Create the section group as below, and say the layout step waits until `fields.flexible` exists.

### Section group missing

`section.layoutType` and `section.groupType` are both null. This is the first dashboard step.

1. In WordPress admin, open Custom Fields, then Field Groups, then Add New.
2. Title, the label at the top of the group: `section: <graphqlName>`.
3. In the group sidebar, Show in GraphQL: Yes. GraphQL Field Name: `<graphqlName>`.
4. Location: Post Type is equal to Post. That is where a section group such as `ImageGrid` or `Interior` is exposed before, and after, it is a layout. Do not add a location for every post type in `core.config.js`. Those post types already read the section through `fields.flexible`.
5. Add the field blocks below on this group, not inside `flexible`.

Then print the flexible parent steps and the layout block.

### Section group exists, not a layout

`section.groupType` is set and `section.onFlexibleUnion` is false. This is the `ImageGrid` state: the group is in GraphQL and it is not a member of `flexible.union`. This is the first dashboard step. Do not click Add New. Do not rename the title. The list title cannot be verified from GraphQL. Open the group whose GraphQL Field Name is `<graphqlName>`.

Add any fragment field that is not already in `tree`. Then print the flexible parent steps and the layout block.

### Already a layout

`section.onFlexibleUnion` is true. This is the first dashboard step. Print the flexible parent steps, then expand the layout whose Layout Name is the folder name. Do not add a second layout. Do not create the section group. Do not add a Clone of it again. Fields already in `tree` are already on that layout. Do not print Add Field for those names.

### Layout block

Print this after the section fields, unless `onFlexibleUnion` is true.

1. On the existing `flexible` field, click Add Layout. Do not click Add Field at the bottom of the `fields` group.
2. Layout Label: the folder name.
3. Layout Name: the folder name, exact case. This becomes `FieldsFlexible<Folder>Layout`. Do not snake_case it. Do not set the layout name to `fields` or to `<graphqlName>`.
4. Inside that layout, click Add Field. This is the only field on the layout.
   - Field Label: the folder name, exact case. Do not insert a space before every capital in a folder such as `Layer01HIGHLIGHTS`.
   - Field Name: `<graphqlName>`.
   - Field Type: Clone.
   - Clone: the section group whose GraphQL Field Name is `<graphqlName>`.
   - Display: Seamless.
   - Prefix Field Names: off.
   - Required: No. Show in GraphQL: Yes. GraphQL Field Name: `<graphqlName>`. Instructions empty. No wrapper class.
5. Leave every other layout as it is.

Seamless is what makes the layout implement the section group's fields the way `FieldsFlexibleInteriorLayout` implements `Interior_Fields`. GraphQL does not report a field type of `clone` after that. The cloned fields appear on the layout.

### Field block

One block per fragment field, on the section group. A field on the group uses Add Field. A field inside a group or a repeater uses Add Sub Field on that parent.

Every block prints all of these lines:

- Where to click.
- Field Label.
- Field Name.
- Field Type, plus the type settings in the list below.
- Required: No.
- Show in GraphQL: Yes.
- GraphQL Field Name: the same string as Field Name.
- Instructions: leave empty.
- Wrapper: do not set a class.

Type settings:

- A plain string in the component is Field Type Text. Not Text Area and not WYSIWYG.
- A group that is not a reusable clone is Field Type Group. Then one block per child. The group name and a child name must differ. `header` and `intro` do. A group named `title` with a child named `title` does not.
- A repeater is Field Type Repeater, Layout: Block, Button Label: `Add Row`, Minimum rows empty, Maximum rows empty. Then one block per child, in fragment order.
- `mediaItem` is Field Type Image, Return Format: Image Array. Not Image URL and not Image ID. Image Array is the setting that exposes the `MediaItem` connection the fragment spreads. One picture is one image field. A hover picture is a second image field with the same settings. It is not desktop and mobile inside one field.
- `responsiveMedia` is Field Type Group. Children are `desktop` and `mobile`, each Field Type Image, Return Format Image Array.
- `responsiveFull` is Field Type Clone of the existing `BackgroundFields` group. Display: Seamless. Prefix Field Names: off. The fragment spreads `...BackgroundFields`. Do not rebuild `type`, `imageFields`, and `videoFields` by hand. Do not add `BackgroundFields` as its own flexible layout. Nest the Clone where the fragment nests the spread.
- `button` is a group or a repeater, as the fragment writes it. Inside that wrapper, Field Type Clone of the existing button group (`ButtonFields` when that is the live type). Display: Seamless. Prefix Field Names: off. Do not rebuild `text`, `variant`, or `actionType` by hand. Do not add `ButtonFields` as its own flexible layout.
- `spacing` is Field Type Group named as in the fragment. Children follow the `...Layout` selection. Do not add spacing fields the fragment does not select.

When `patterns.examples` has that shape's key, the block names that section and says to clone the same source group it uses, then still prints Field Name and GraphQL Field Name so the copy matches this fragment. When the key is absent, the field is new. Do not name a section `patterns` did not return.

### Close

Click Update on the section group, then Update on the `fields` group after the layout clone. The fragment cannot resolve until this layout exists. When `check-fragment` has `onExists` false and `comparedTo` null, do not say the schema matches.

## What this stage must not do

- Do not add a field group, PHP registration, or `acf-json` to the Next repo. That ban does not stop the field report from telling the human to create the section group in the WordPress dashboard when `section.layoutType` and `section.groupType` are both null. The report never tells the human to create the `fields` group. When `flexibleField` is set, the report opens that group and does not add a second flexible field. Do not import or sync a field group. This stage still must not load `skills/acf-section-fields/`.
- Do not import or merge a layout from another site.
- Do not write the fragment from string literals in the Figma export when `section` or `patterns` already has a shape for that content.
- Do not write an audit markdown file or `field-report.md` under this stage `output/`.
