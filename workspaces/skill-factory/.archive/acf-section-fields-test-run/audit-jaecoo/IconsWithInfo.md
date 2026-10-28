# ACF audit: IconsWithInfo

- Repo: `/home/dev/jaecoo-next/code`
- Frontend contract: **found**
- GraphQL type the app expects: `FieldsFlexibleIconsWithInfoLayout`
- Parent: field group GraphQL name `fields`, flexible field `flexible`
- Location post types: model, page, article, serviceCenter, showRoom
- WordPress: Unknown. Field groups are not in git. Confirm this layout on the target environment.

Do not create a new field group for this section. Add a layout to the existing flexible field.
Repeat this on each environment from that environment's own export. Do not import a dev file into production.

Frontend fragment: `/home/dev/jaecoo-next/code/app/components/Sections/IconsWithInfo/IconsWithInfo.gql`

## Fields

| Field | Type |
| --- | --- |
| `title` | text |
| `description` | wysiwyg or text |
| `iconList` | repeater |
| `iconList.icon` | clone of MediaItem |
| `iconList.description` | wysiwyg or text |
| `buttonFields` | clone of ButtonItem |
| `comment` | text |
| `layout` | clone of Layout |

Renderer props, not ACF fields: `order`

## Apply on one environment

1. In that environment, export the field group whose GraphQL field name is `fields` (Custom Fields → Tools → Export).
2. From the skill folder, run `scripts/patch_acf_export.py --export <that-file> --spec <section.spec.json>`.
3. If the script writes a patched file, import it on the **same** environment (Tools → Import). If it reports missing clone fields, add those by cloning the sibling layout's field in the admin instead of importing a partial file.
4. Confirm the layout name and that Show in GraphQL is on. The layout `__typename` must be `FieldsFlexibleIconsWithInfoLayout`.
5. Open a page that uses the section, or run the site's `npm run gql` against this environment, and confirm the fragment validates.

Without an export, create the layout by hand from the table above. Copy `layout`, `buttonFields`, and responsive image fields from an existing layout (clone, seamless) so the shared fragments keep resolving.

## Frontend fragment

```graphql
fragment IconsWithInfo on FieldsFlexibleIconsWithInfoLayout {
  title
  description
  iconList {
    icon {
      ...MediaItem
    }
    description
  }
  buttonFields {
    ...ButtonItem
  }
  comment
  ...Layout
}
```
