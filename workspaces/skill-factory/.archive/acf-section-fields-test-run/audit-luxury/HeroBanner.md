# ACF audit: HeroBanner

- Repo: `/home/dev/colmobil-luxury-trade/code`
- Frontend contract: **found**
- GraphQL type the app expects: `FieldsFlexibleHeroBannerLayout`
- Parent: field group GraphQL name `fields`, flexible field `flexible`
- Location post types: page, article, center
- WordPress: Unknown. Field groups are not in git. Confirm this layout on the target environment.

Do not create a new field group for this section. Add a layout to the existing flexible field.
Repeat this on each environment from that environment's own export. Do not import a dev file into production.

Frontend fragment: `/home/dev/colmobil-luxury-trade/code/app/components/Sections/HeroBanner/HeroBanner.gql`

Other site: `/home/dev/jaecoo-next/code` also has `HeroBanner`, with different fields. Only there: additionalButtonFields, additionalButtonFields.dataEventName, additionalButtonFields.dataText, additionalButtonFields.displayIcon, additionalButtonFields.exteriorUrl, additionalButtonFields.functionName, additionalButtonFields.interiorUrl, additionalButtonFields.interiorUrl.nodes, additionalButtonFields.interiorUrl.nodes.id, additionalButtonFields.interiorUrl.nodes.slug, additionalButtonFields.interiorUrl.nodes.uri, additionalButtonFields.isNewWindow, additionalButtonFields.label, additionalButtonFields.labelMobile, additionalButtonFields.model, additionalButtonFields.model.nodes, additionalButtonFields.model.nodes.id, additionalButtonFields.model.nodes.modelListCodes, additionalButtonFields.model.nodes.modelListCodes.modelFamily, additionalButtonFields.sectionId, additionalButtonFields.type, additionalButtonFields.variant, buttonFields, buttonFields.dataEventName, buttonFields.dataText, buttonFields.displayIcon, buttonFields.exteriorUrl, buttonFields.functionName, buttonFields.interiorUrl, buttonFields.interiorUrl.nodes, buttonFields.interiorUrl.nodes.id, buttonFields.interiorUrl.nodes.slug, buttonFields.interiorUrl.nodes.uri, buttonFields.isNewWindow, buttonFields.label, buttonFields.labelMobile, buttonFields.model, buttonFields.model.nodes, buttonFields.model.nodes.id, buttonFields.model.nodes.modelListCodes, buttonFields.model.nodes.modelListCodes.modelFamily, buttonFields.sectionId, buttonFields.type, buttonFields.variant, imageFields, imageFields.desktop, imageFields.desktop.node, imageFields.desktop.node.alt, imageFields.desktop.node.sizes, imageFields.desktop.node.sizes.height, imageFields.desktop.node.sizes.width, imageFields.desktop.node.src, imageFields.mobile, imageFields.mobile.node, imageFields.mobile.node.alt, imageFields.mobile.node.sizes, imageFields.mobile.node.sizes.height, imageFields.mobile.node.sizes.width, imageFields.mobile.node.src, modelFamily, showStars, subtitle, subtitleBottom, title, type, videoFields, videoFields.desktop, videoFields.desktop.node, videoFields.desktop.node.alt, videoFields.desktop.node.sizes, videoFields.desktop.node.sizes.height, videoFields.desktop.node.sizes.width, videoFields.desktop.node.src, videoFields.mobile, videoFields.mobile.node, videoFields.mobile.node.alt, videoFields.mobile.node.sizes, videoFields.mobile.node.sizes.height, videoFields.mobile.node.sizes.width, videoFields.mobile.node.src. Only here: bannerCards, bannerCards.heroBannerMedia, bannerCards.heroBannerMedia.imageFields, bannerCards.heroBannerMedia.imageFields.desktop, bannerCards.heroBannerMedia.imageFields.desktop.node, bannerCards.heroBannerMedia.imageFields.desktop.node.alt, bannerCards.heroBannerMedia.imageFields.desktop.node.src, bannerCards.heroBannerMedia.imageFields.mobile, bannerCards.heroBannerMedia.imageFields.mobile.node, bannerCards.heroBannerMedia.imageFields.mobile.node.alt, bannerCards.heroBannerMedia.imageFields.mobile.node.src, bannerCards.heroBannerMedia.type, bannerCards.heroBannerMedia.videoFields, bannerCards.heroBannerMedia.videoFields.desktop, bannerCards.heroBannerMedia.videoFields.desktop.node, bannerCards.heroBannerMedia.videoFields.desktop.node.alt, bannerCards.heroBannerMedia.videoFields.desktop.node.src, bannerCards.heroBannerMedia.videoFields.mobile, bannerCards.heroBannerMedia.videoFields.mobile.node, bannerCards.heroBannerMedia.videoFields.mobile.node.alt, bannerCards.heroBannerMedia.videoFields.mobile.node.src, bannerCards.heroBannerSubtitle, bannerCards.heroBannerTitle.

## Fields

| Field | Type |
| --- | --- |
| `layout` | clone of Layout |
| `bannerCards` | repeater |
| `bannerCards.heroBannerSubtitle` | text |
| `bannerCards.heroBannerTitle` | text |
| `bannerCards.heroBannerMedia` | clone of ResponsiveFullMediaItem |

## Apply on one environment

1. In that environment, export the field group whose GraphQL field name is `fields` (Custom Fields → Tools → Export).
2. From the skill folder, run `scripts/patch_acf_export.py --export <that-file> --spec <section.spec.json>`.
3. If the script writes a patched file, import it on the **same** environment (Tools → Import). If it reports missing clone fields, add those by cloning the sibling layout's field in the admin instead of importing a partial file.
4. Confirm the layout name and that Show in GraphQL is on. The layout `__typename` must be `FieldsFlexibleHeroBannerLayout`.
5. Open a page that uses the section, or run the site's `npm run gql` against this environment, and confirm the fragment validates.

Without an export, create the layout by hand from the table above. Copy `layout`, `buttonFields`, and responsive image fields from an existing layout (clone, seamless) so the shared fragments keep resolving.

## Frontend fragment

```graphql
fragment HeroBanner on FieldsFlexibleHeroBannerLayout {
  ...Layout
  bannerCards {
    heroBannerSubtitle
    heroBannerTitle
    heroBannerMedia {
      ...ResponsiveFullMediaItem
    }
  }
}
```
