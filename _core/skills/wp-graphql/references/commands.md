# Command output

Every command prints one JSON object. `summary` is a list of short facts. The other fields are there when a fact needs the underlying names.

## status

| Field | Meaning |
|---|---|
| `endpointHost` | Host of the GraphQL endpoint. No path, no query string. |
| `authenticated` | The endpoint accepted the call. |
| `schemaCached` | A schema cache for this endpoint is still inside 15 minutes and matches the current cache shape. |

## patterns

| Field | Meaning |
|---|---|
| `flexible.union` | The Hebrew flexible layout type when it exists, otherwise the first one found. The GraphQL type is a union or an interface whose possible types are all layouts. A wider interface that only contains some layouts, such as `AcfFieldGroup`, is not this type. The key stays `union` either way. |
| `flexible.paths` | `Page`, `Post`, `Model`, and `Article` paths for that layout type. |
| `flexible.unions` | One entry per flexible layout type: `union`, `language` (`he` or `en`), `paths`, and `layouts`. |
| `flexibleField` | The flexible-content field reached by `fields` or `enFields`, or null when that field is absent. `parentType` is the group type that owns it. `parentField` is `fields` or `enFields`. `field` is the field name (`flexible` or `enFlexible`). `gqlType` is that field's GraphQL type as written, for example `[FieldsFlexible_Layout]`. `named` is the bare type name. The type `named` points at is always treated as the layout list, even when a stray possible type that is not a layout is also on it. This is set when the field exists even if `flexible` is null because the layout list has fewer than two layouts. Hebrew `fields` / `flexible` wins over English when both exist. |
| `counts` | Layout count and shape counts for `flexible.union`. |
| `examples` | First section and field path found for each shape on `flexible.union`. |
| `layouts` | One entry per layout on every flexible layout type: `section`, `layout` type, `language`, top-level `fields`, and `shapes`. |
| `options` | ACF options-page root fields: `parent`, `field`, `type`. |
| `templates` | `Template_*` object types that own a field group, with the group field names. |

`summary` names both layout types. It does not list Comment, Color, or other non-content types. The options and template lines are the names to pass to `type`. It does not include the WordPress admin title of a field group.

## section NAME

Looks up `FieldsFlexible<Name>Layout`, then `EnFieldsEnFlexible<Name>Layout`, then an object type whose name matches `Name`.

| Field | Meaning |
|---|---|
| `layoutType` | The flexible layout type, or null. When the type exists but is not on the flexible layout type, `layoutType` is set, `onFlexibleUnion` is false, and `summary` says so. |
| `onFlexibleUnion` | Whether that layout is a member of a flexible layout type. That type is a union or an interface. |
| `groupType` | A field-group object type named like the section, or null. |
| `exposedAs` | `Parent.field` pairs whose field type is that group or layout. |
| `tree` | Nested fields of the layout, or of the group when there is no layout. Each node has `name`, `gqlType`, `namedType`, `acfType`, `shape`, `children`. A `mediaItem` node also has `imageOn`: `edge` or `mediaItem`. A connection edge is expanded one level so `node` is visible. Other connection types are not expanded. `choices` is present when the description listed them. |
| `fragment` | Comparison against `Sections/<Name>/<Name>.gql` under `app/` or `code/app/` when that file exists. `onExists` is false when the fragment's type is absent. `missingOnSchema` lists selected fields the compared type does not have. `notSelected` lists top-level live fields the fragment left out. `shapeMismatches` lists a field whose spread expects a different shape than the live type. `deprecatedSelected` lists selected fields the schema marks deprecated, such as `mediaItemId`; they are not missing. Trees and `notSelected` leave deprecated fields out. A media spread on a connection edge matches when the fragment's body is `node { ... }`, and that body is compared on the edge. A media spread whose body is not `node { ... }`, a double `node`, and a media spread on a gallery connection are reported. Inline fragments are compared on their own type. |
| `similarLayout` | Another flexible layout that shares the most field names. This is not an ACF clone. `basedOn` is `fragment` when the fragment matches, and `live` when it does not. `cloneFrom` is the same object. |

When the fragment targets a missing layout type and a group type exists, the field comparison uses the group type and `fragment.comparedTo` names it.

`fragment.compared` is false when no type was compared. Then `missingOnSchema` and `shapeMismatches` are empty because nothing was checked, and `summary` says "No type was compared. The fragment fields were not checked." That is not a match.

A live-field label `clone of SomeType` means the GraphQL type is a reused ACF clone, not `similarLayout`.

## type NAME

Same tree, exposure, and fragment comparison as `section`, for a GraphQL object, a root field such as `siteSettings` or `carsBoardSettings`, or a template type. `rootField` is `RootQuery.field` when the name is a root field. `type` is the object that was read.

## choices Type.field

| Field | Meaning |
|---|---|
| `type` | The object type that owns the field. |
| `field` | The field name as it appears in the schema. |
| `acfType` | Parsed ACF field type, or null when the description did not name one. |
| `gqlType` | GraphQL type string. |
| `choices` | Enum values, or choice strings parsed from the field description. |

Exit 5 `CHOICES_UNAVAILABLE` when neither source has an option list. The agent stops.

## check-fragment FILE

Same fragment fields as `section`, for the first fragment in the file, plus `onFlexibleUnion` and `exposedAs` for the type the fragment names.

## check-repo

Compares every fragment under `app/` and `code/app/`. `checked` is the number read. `problems` lists only files whose fragment has `missingOnSchema` or `shapeMismatches`. `notCompared` lists fragments whose `on` type is not in the schema, such as shared `on TYPE` fragments or a layout that does not exist yet. Those were not checked, so `summary` never says every fragment matches while `notCompared` is non-empty.

## diff-group NAME --plan FILE

Compares a field plan with the live layout (or group) for section NAME, using the same tree as `section`. This section defines the plan JSON.

Top level: `schemaVersion` (must be 1), `fields` (required), and optional `folder`, `graphqlName`, `layoutType`, `route` and `questions`, which the command does not read.

| Field key | Meaning |
|---|---|
| `name` | Required. The GraphQL field name, a GraphQL name |
| `label` | ACF Field Label. Not compared |
| `acfType` | ACF type (`text`, `textarea`, `wysiwyg`, `image`, `link`, `group`, `repeater`, `clone`, `select`, `true_false`). Compared only when the live field names one |
| `shape` | `mediaItem`, `responsiveMedia`, `responsiveFull`, `button` or `spacing`. Compared with the live shape |
| `cloneOf` | The GraphQL type a Clone reuses. Compared with the live `namedType` |
| `min`, `max` | Repeater rows. GraphQL cannot see them |
| `list` | True for a list. Derived from `acfType` when absent |
| `children` | Sub-fields, same keys |

A plan over 256 KB, nested deeper than 6 levels, with unknown keys, or with a field name that is not a GraphQL name is a `USAGE` error.

| Field | Meaning |
|---|---|
| `matches` | True when the section exists and every list below is empty. |
| `added` | Dotted paths in the plan that are not live. |
| `removed` | Live paths not in the plan. `fieldGroupName` is ignored. |
| `typeChanged` | `{path, reason}` when `shape`, `cloneOf` (against `namedType`) or `acfType` differ. `acfType` is compared only when both sides have it. |
| `cardinalityChanged` | `{path, plan, live}` when one side is a list and the other is not. The plan side is `list`, or derived from `acfType` (repeater, gallery, relationship, flexible content). |
| `unknown` | Settings GraphQL cannot show: title, location, min/max, required, Seamless. |

Children of a field with a shared `shape` (media, button, spacing) are not compared.

## Shared flags

- `--repo` (required): Next app root. The store is `dist/dev/cache/store.json` under that root, or `code/dist/dev/cache/store.json`.
- `--store`: another store file.
- `--refresh`: sign in again and reload the schema.
- `WP_GQL_ENDPOINT` and `WP_GQL_TOKEN` replace the store when both are set. `WP_GQL_DEV_HEADER` is optional with those.
