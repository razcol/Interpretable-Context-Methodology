# field-plan.json

The field plan as data. Stage 02 writes it, `wp-graphql diff-group --plan` reads it, and stage 03 writes the fragment from it. This file defines the top-level keys for this workspace.

```json
{
  "schemaVersion": 1,
  "folder": "ImageGrid",
  "graphqlName": "imageGrid",
  "layoutType": "FieldsFlexibleImageGridLayout",
  "route": "new",
  "fields": [
    { "name": "intro", "label": "Intro", "acfType": "textarea" },
    { "name": "grid", "label": "Grid", "acfType": "repeater", "min": 6, "max": 6, "children": [
      { "name": "media", "label": "Media", "shape": "responsiveFull", "cloneOf": "BackgroundFields" },
      { "name": "title", "label": "Title", "acfType": "text" },
      { "name": "text", "label": "Text", "acfType": "textarea" }
    ]},
    { "name": "disclaimer", "label": "Disclaimer", "acfType": "text" }
  ],
  "questions": [
    { "id": "touch", "text": "Does the hover-only text show on touch screens?", "answer": "yes, always shown below 1279px" }
  ]
}
```

## Keys

| Key | Required | Meaning |
|---|---|---|
| `schemaVersion` | yes | `1` |
| `folder` | yes | Folder name, equal to the ACF Layout Name |
| `graphqlName` | yes | Folder name with its first character lowercased |
| `layoutType` | yes | `FieldsFlexible<Folder>Layout`, or `EnFieldsEnFlexible<Folder>Layout` on an English-only site |
| `route` | yes | `new` or `sync` |
| `fields` | yes | Top-level fields, in fragment order |
| `questions` | no | Questions from the plan, with your answers once you give them |

Each field's keys (`name`, `label`, `acfType`, `shape`, `cloneOf`, `min`, `max`, `list`, `children`) and what `diff-group` compares are defined in the wp-graphql skill, `references/commands.md`, section "diff-group". This workspace adds one rule: `min` and `max` carry the slot count when the design has a fixed number of cards.

`diff-group` rejects unknown keys, names that are not GraphQL names, nesting deeper than 6, files over 256 KB and any `schemaVersion` other than 1.
