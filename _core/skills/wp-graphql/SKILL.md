---
name: wp-graphql
description: "Run fixed commands against this project's WordPress GraphQL schema for ACF sections, options pages, and templates. Use when the task needs live section patterns, where a type is attached, the field tree for a section or type name, select choices, a check of one .gql fragment or every fragment in the repo, or a comparison of a field plan with the live group. Pass the section name, Type.field, or fragment path. Do not write a GraphQL query, introspection, or sign-in script."
---

# WP GraphQL

The commands below already know how this project signs in and how ACF sections are shaped. Run one of them. Do not open `scripts/wp_graphql.py`, the project store, or `~/.cache/wp-graphql/`. Do not request a token or write a query.

Run the script from this skill folder. `--repo` is the Next app the user already named. Fragments live under `app/` or `code/app/` in that repo.

```bash
python3 scripts/wp_graphql.py status --repo /path/to/next
python3 scripts/wp_graphql.py patterns --repo /path/to/next
python3 scripts/wp_graphql.py section INTERIOR --repo /path/to/next
python3 scripts/wp_graphql.py type carsBoardSettings --repo /path/to/next
python3 scripts/wp_graphql.py choices ButtonFields.variant --repo /path/to/next
python3 scripts/wp_graphql.py check-fragment /path/to/File.gql --repo /path/to/next
python3 scripts/wp_graphql.py check-repo --repo /path/to/next
python3 scripts/wp_graphql.py diff-group ImageGrid --plan /path/to/field-plan.json --repo /path/to/next
```

Add `--refresh` only when the user just changed ACF and the cached schema would be stale. The cache lasts 15 minutes.

## Which command

| The task needs | Command | Read |
|---|---|---|
| Can this repo reach GraphQL? | `status` | `endpointHost`, `authenticated` |
| How do sections, images, buttons, and spacing work on this site? | `patterns` | `summary`, then `examples` |
| What is section NAME on the server right now, and does its fragment match? | `section NAME` | `summary`, then `tree` |
| What is an options page, template, or other type that is not a flexible layout? | `type NAME` | `summary`, then `tree` |
| What are the select options for one field? | `choices Type.field` | `summary`, then `choices` |
| Does this one fragment match the live type? | `check-fragment FILE` | `summary` |
| Which fragments in this repo select a field the schema does not have? | `check-repo` | `summary`, then `problems` and `notCompared` |
| Does the ACF group the user built match a field plan? | `diff-group NAME --plan FILE` | `matches`, then `summary` |

`section` looks for `app/components/Sections/<Name>/<Name>.gql` or `code/app/components/Sections/<Name>/<Name>.gql` and includes that comparison. Use `check-fragment` when the file is somewhere else. Use `type` for `siteSettings`, `carsBoardSettings`, `Template_ContactUs`, and any other name that is not a flexible layout.

`summary` is the answer. `tree` is the field hierarchy when the user needs every nested name. Do not run a second command to restate what `summary` already says.

A null `acfType` means the schema description did not name an ACF field type. It does not mean the field has no options. `choices` is the command for the option list. On `CHOICES_UNAVAILABLE`, stop. Do not look in another repo, REST, or the database.

`...MediaItem` is the `mediaItem` shape. Deprecated fields, such as `mediaItemId` on `MediaItem`, are listed under `fragment.deprecatedSelected`, not as missing, and `section` trees leave them out. A shared media fragment whose whole body is `node { ... }`, such as the repos' `MediaItem` and `MediaItemNew`, is written for a connection edge: `image { ...MediaItem }` on an `AcfMediaItemConnectionEdge` field matches, and the body is compared on the edge. A media spread whose body is not `node { ... }` on an edge is a real mismatch, and so is `node { ...MediaItem }` (two `node` levels). A gallery field (`AcfMediaItemConnection`) has `nodes`, not `node`. Inline fragments (`... on Model { }`) are compared on their own type. `check-fragment` also lists live fields the file did not select.

For a flexible section, follow the Page, Post, Model, and Article paths in `summary`. Hebrew layouts are `fields.flexible` (`FieldsFlexible…Layout`). English layouts are `enFields.enFlexible` (`EnFieldsEnFlexible…Layout`). `flexibleField` is set when that field exists even if `flexible` is null because the layout list has fewer than two layouts. A null `flexible` with a set `flexibleField` means the `fields` group is already there. `flexible.union` is the GraphQL type that lists the layouts. That type is a union or an interface. The key name stays `union` either way. Do not read an admin title from this command. The schema does not carry it. For an options page or a template, use `type` on the name in the options or template line. A field label `clone of SomeOtherType` is an ACF clone's GraphQL type. `similarLayout` is a different layout with similar field names, not an ACF clone.

## What the shapes mean

These labels are on `patterns` examples and on `section` tree nodes. Use them as the field shape. Do not re-derive them from raw GraphQL types. Do read `namedType` when the summary says the field is a clone of that type, and `imageOn` when a `mediaItem` is `edge` rather than `mediaItem`.

| Shape | What it is |
|---|---|
| `mediaItem` | One image. On a connection edge (`imageOn` is `edge`), spread the repo's shared media fragment whose body is `node { ... }`, for example `image { ...MediaItem }`. |
| `responsiveMedia` | A group with `desktop` and `mobile`, each a `mediaItem`. |
| `responsiveFull` | A group with `type`, `imageFields`, and `videoFields`. The shared spread is `BackgroundFields`. |
| `spacing` | `layout.marginBottom.desktop` and `mobile`. |
| `button` | The shared button fields (`actionType`, `text`, and the link groups). |

## Output

Success is `{"ok": true, ...}` and exit 0. A section that is not a flexible layout is still success. The `summary` says so.

Failure is `{"ok": false, "error": {"code", "message"}}`.

| Exit | Code | What to do |
|---|---|---|
| 1 | `USAGE` | Fix the arguments. |
| 2 | `AUTH_FAILED` | The repo store or `WP_GQL_ENDPOINT` / `WP_GQL_TOKEN` is missing or rejected. Do not invent another sign-in. |
| 3 | `HTTP_FAILED` or `SCHEMA` | The endpoint did not answer. Retry once with `--refresh`. |
| 4 | `FILE_NOT_FOUND` | The fragment or plan path is wrong. |
| 5 | `CHOICES_UNAVAILABLE` | The option list is not in the GraphQL schema. Stop. |
| 99 | `INTERNAL` | Report the command and stop. |

## Secrets

The JSON does not include tokens or store values. Do not pass `--show` flags, print the cache under `~/.cache/wp-graphql/`, or copy the store into the chat. `endpointHost` is the host only.

Output fields are listed in [references/commands.md](references/commands.md).
