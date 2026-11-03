# Fragment rules

How the live `tree` from `section <Folder>` becomes the `.gql` selection. The command JSON is the truth. `core.config.js`, page templates and other sections' `.gql` files are not evidence that a field or group exists.

## The fragment line

```graphql
fragment <Folder> on <layoutType> {
  ...
}
```

`layoutType` is `section.layoutType` (`FieldsFlexible<Folder>Layout`, or `EnFieldsEnFlexible<Folder>Layout` on an English-only site). The fragment name is the folder name.

## Fields

- Use each node's `name` as saved, even when it differs from the plan's spelling. `diff-group` already confirmed they agree.
- Leave out `fieldGroupName`.
- A node with a `shape` becomes that shape's shared spread. Never write its inner fields by hand.
- A node without a shape: a scalar is selected by name; a group or repeater is selected with its children, recursively.
- Add `...Layout` only when the plan has spacing.

## Shared spreads

Names come from the repo profile's `fragments` (the fragment name, not the file name):

| `shape` | Selection |
|---|---|
| `responsiveFull` | `<field> { ...<backgroundFields> }` |
| `responsiveMedia` | `<field> { ...<responsiveMedia> }` |
| `mediaItem` | `<field> { ...<mediaItem> }`. The repo's media fragment already selects `node`, so it goes directly on the image field. `node { ...MediaItem }` is wrong |
| `button` | `<field> { ...<button> }` (`Button` in ora, `ButtonItem` elsewhere) |
| `spacing` | `...<layout>` |

Use `MediaItemNew` or `ResponsiveMediaItemNew` only when the component reads `src` and `alt` (stage 04 decides; default to `MediaItem`). A spread name that is not in the repo silently becomes `__typename`, so every spread must exist in the profile's `fragments` or in another repo `.gql`.

When `patterns.examples` names a section for a shape and that section's `.gql` uses a different spread, follow that section's spread.

## Reading check-fragment

| Result | Meaning | Do |
|---|---|---|
| `compared` false | The layout type is not in the schema | Stop at the checkpoint. The layout is not saved yet |
| `missingOnSchema` | A selected field the live type lacks | Fix the name or remove the field |
| `shapeMismatches` | A spread that does not fit the live field (for example a flat media spread on an edge, or a spread on a gallery, which needs `nodes`) | Use the shared fragment the table above names |
| `deprecatedSelected` | Deprecated fields inside shared fragments, such as `mediaItemId` | Leave them |
| `notSelected` | Live fields the file does not select | Select them unless the plan says why not |
