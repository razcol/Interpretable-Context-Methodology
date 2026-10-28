# Field patterns

These notes are for Jaecoo (`/home/dev/jaecoo-next`) and luxury trade (`/home/dev/colmobil-luxury-trade`). Both are headless Next.js apps. WordPress is a separate multisite. ACF field groups are in that database, not in git.

## The only parent these sections use

| Piece | Value |
| --- | --- |
| Field group, GraphQL name | `fields` |
| Flexible field name | `flexible` |
| Layout GraphQL type | `FieldsFlexible` + folder name + `Layout` |
| Fragment file | `code/app/components/Sections/<Folder>/<Folder>.gql` |
| Post types, Jaecoo | `page`, `model`, `article`, `serviceCenter`, `showRoom` |
| Post types, luxury trade | `page`, `article`, `center` |

`core.config.js` `flexiblePath` is the source for the group and field names. Re-read it if the repo is a different brand. A normal new section does not need a `core.config.js` edit. The directory scanner picks up the folder.

Folder name, fragment name, and the layout name that produces the GraphQL type are the same string, including odd casing such as `Categoriescarousel`. Do not snake_case a layout name unless an export of the target site shows that every existing layout is snake_case. Then confirm the live `__typename` before importing.

## Shared fragments

Defined under `code/app/fragments/global/`. Luxury trade also has `code/app/fragments/shared/` for shapes reused on an options page and a layout. Copy the sibling ACF field (clone, seamless) instead of rebuilding it.

| Fragment | ACF shape the components expect |
| --- | --- |
| `Layout` | Group `layout` → `marginBottom.desktop` and `marginBottom.mobile` (numbers) |
| `ButtonItem` | Group `buttonFields`. Not an ACF link field. Select `type` is `page_link`, `url`, `action`, or `navToSection`. Relationship `interiorUrl` differs by site: Jaecoo includes `Model`, `ServiceCenter`, `ShowRoom`; luxury trade includes `Center`. |
| `MediaItem` | Image field queried as `{ node { src: mediaItemUrl, alt: altText } }`. Jaecoo also selects `mediaDetails { width height }`. Not a URL string and not a bare attachment ID in the query. |
| `ResponsiveMediaItem` | Group with `desktop` and `mobile`, each a `MediaItem` |
| `ResponsiveFullMediaItem` | Select `type` plus `videoFields` and `imageFields`, each desktop/mobile |

`order` on the React component is injected by `@colmobil/next`. It is not an ACF field.

## What "already exists" means

- The `.gql` file exists: the frontend already expects the layout. Production may still be behind. Say so.
- The `.gql` file is absent: propose a new layout on the existing flexible field.
- The same folder on the other site with a different fragment: do not copy that site's field list. Known differences include `HeroBanner`, `ImageWithInfo`, `ArticlePreview`, `ContactUs`, and `QuestionsAnswers`.

Options pages (`siteSettings`, `purchaseSettings`, `yomanSettings`, and the luxury board pages) are not flexible layouts. Do not append them as layouts. A template field group (`Template_ContactUs`, `contactUsTemplateFields`) is also a different location rule.

## Import rules

- Export the group on the environment you are about to change. Patch that file. Import it there.
- Do not import a dev export into production. Production has its own keys and its own content edits.
- The patcher refuses to write a file when a cloned field has no sibling of the same name. Add that field in the admin by cloning the existing one.
- The patcher does not change the group key and does not edit a subfield that is already on the layout.
- `scripts/inspect_acf_layout.php` only reads. Run it with `wp eval-file` and `--url` for the site whose database you mean. It is the check for "does this environment have the layout". The Next repo cannot answer that.
