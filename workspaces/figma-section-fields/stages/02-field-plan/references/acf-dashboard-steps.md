# ACF dashboard steps

The click blocks the field report is built from. `<graphqlName>` is the folder name with its first character lowercased (`ImageGrid` becomes `imageGrid`). It is a GraphQL name, not a label with spaces.

## Section group missing

1. In WordPress admin, open Custom Fields, then Field Groups, then Add New.
2. Title: `section: <graphqlName>`.
3. In the group settings: Show in GraphQL: Yes. GraphQL Field Name: `<graphqlName>`.
4. Location: the rule the field report derived from `exposedAs` or `patterns`.
5. Add one field block per plan field, on this group.
6. Click Save Changes (older ACF: Update). The layout's Clone needs the saved group.

## Open an existing group

1. In WordPress admin, open Custom Fields, then Field Groups.
2. Open the group whose GraphQL Field Name is `<graphqlName>`. Its list title cannot be checked from GraphQL; match it by GraphQL Field Name.
3. Add a field block only for plan fields that are not in the live `tree`.

## Flexible parent

1. Open the group whose GraphQL Field Name is `fields`. Do not click Add New. Do not change its location rules.
2. Find the field whose Field Name is `flexible`. Its type is already Flexible Content. Expand it.
3. When the layout already exists (`onFlexibleUnion` true), expand the layout whose Layout Name is `<Folder>`. Do not add a second layout.

## Layout block

1. On the `flexible` field, click Add Layout.
2. Layout Label: `<Folder>`. Layout Name: `<Folder>`, exact case. This becomes `FieldsFlexible<Folder>Layout`.
3. Inside the layout, click Add Field. It is the only field on the layout:
   - Field Label: `<Folder>`. Field Name: `<graphqlName>`. Field Type: Clone.
   - Fields: the section group whose GraphQL Field Name is `<graphqlName>`.
   - Display: Seamless. Prefix Field Names: off.
   - Required: No. Show in GraphQL: Yes. GraphQL Field Name: `<graphqlName>`.
4. Leave the other layouts as they are. Click Save Changes (older ACF: Update) on the `fields` group.

Seamless puts the section group's fields on the layout itself, so the fragment selects them directly on `FieldsFlexible<Folder>Layout`.

## Field block

One block per plan field. A field on the group uses Add Field. A field inside a group or repeater uses Add Sub Field on that parent, and is written indented under it.

Every block lists:

- Where to click.
- Field Label: from the plan's `label`, or the name with a space before each capital and the first letter capitalized (`cardsList` is `Cards List`).
- Field Name: the plan's `name`. Overwrite the slug ACF generates (`cards_list`).
- Field Type and its settings, from the list below.
- Required: No. Show in GraphQL: Yes. GraphQL Field Name: the same as Field Name. Instructions empty. No wrapper class.

Type settings:

| Plan | ACF setting |
|---|---|
| `text` | Text |
| `textarea` | Text Area, New Lines: No Formatting |
| `wysiwyg` | WYSIWYG Editor |
| `link` | Link, Return Format: Link Array |
| `group` | Group, Layout: Block. Then one block per child. A group and its child never share a name |
| `repeater` | Repeater, Layout: Block, Button Label `Add Row`, Minimum and Maximum rows from the plan (empty when the plan has none). Then one block per child |
| `mediaItem` | Image, Return Format: Image Array |
| `responsiveMedia` | Group with `desktop` and `mobile`, each Image, Return Format: Image Array |
| `responsiveFull` | Clone of the existing `BackgroundFields` group, Display: Seamless, Prefix Field Names: off. Do not rebuild `type`, `imageFields` and `videoFields` by hand |
| `button` | Group (one) or Repeater (several) holding a Clone of the existing button group, Display: Seamless, Prefix Field Names: off |
| `spacing` | Clone of the existing layout spacing group, only when the plan has it |

When `patterns.examples` names a section for that shape, the block says "clone the same source group as `<Section>`" and still lists Field Name and GraphQL Field Name.
