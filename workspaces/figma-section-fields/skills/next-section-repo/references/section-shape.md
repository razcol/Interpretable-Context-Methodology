# Section shape

A section is one folder under the repo's sections directory (`profile.sectionsDir`, usually `app/components/Sections`). Its name is the ACF Layout Name. The repo profile, defined in [repo-profile.md](repo-profile.md), holds every value that differs between repos.

## Files

These come from `ccTemplates/section.js` (`profile.scaffold.files`, with `{F}` as the folder name):

| File | Holds |
|---|---|
| `index.js` | `import F from './ServerF'; export default F;` |
| `ServerF.js` | `import 'server-only';` first. Reads `layout`, `order` and the fragment fields from props, and fetches anything that is not a section field |
| `ClientF.js` | `'use client';` first. Renders `<StyledF id={order}>` and the markup. Declares `propTypes` for every prop |
| `StyledF.js` | One `styled.div` with nested role class names (`.card`, `.card-title`) |
| `F.gql` | `fragment F on FieldsFlexibleFLayout { ... }` with the shared spreads from `profile.fragments` |

`field-report.md` may sit beside them while you build the ACF group. It is a helper, not part of the section.

## Data

Section fields are what an editor changes per section: text, media, links, repeaters. Page data is never a field: breadcrumbs (`profile.breadcrumbs`), SEO, the page title, the section order, and model or site context.

Images come from WordPress through the fragment. The folder holds no image files.

## Styles

- Fonts come from `theme.fonts.<export>` (`profile.theme.fonts`). Colors that match `profile.theme.colors` use `theme.colors.<path>`.
- The root is fluid: `width: 100%` and a `max-width` at the design width, with no fixed height.
- Mobile rules (breakpoints, nesting, hover and touch, media pairs) follow [mobile-patterns.md](mobile-patterns.md).
- `theme.mixins.layout` only when `layout` is in `profile.theme.mixins`.
- The page is right to left (`profile.pageDirection`). The section root is `direction: ltr`, so flex rows keep Figma's order, and Hebrew text sets `direction: rtl` itself.
- Line endings follow `profile.eol`.
