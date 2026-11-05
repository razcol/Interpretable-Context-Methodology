# Section conformance checklist

What a finished section must look like in any of your Next.js section repos. Repo-specific values (file set, fragment names, theme keys, line endings) come from the repo profile, defined in [repo-profile.md](repo-profile.md). The check id says which `check_section.py` row enforces the item. "manual" means the agent checks it by reading, and "verify" means stage 05 checks it in a browser.

The bracketed session ids are where you had to fix the item by hand. They come from the 2026-11-03 audit.

## Folder and files

| Item | Check |
|---|---|
| The folder name is PascalCase and equals the ACF Layout Name. The runtime maps `FieldsFlexible<F>Layout` back to the folder name [9a7ff2cc renamed `Layer01HIGHLIGHTS` to `ImageGrid`] | `folder-name` |
| The folder name has no `Server` and equals no global fragment name. Sections load last into `globalFragments`, so a clash overrides that fragment site-wide | `folder-name` |
| The files are the profile's `scaffold.files`: `index.js` re-exports `./Server<F>`, `Server<F>.js` starts with `import 'server-only';`, `Client<F>.js` starts with `'use client';`, plus `Styled<F>.js` and `<F>.gql` [9a7ff2cc, ccca3c08] | `files-present`, `server-only`, `use-client` |
| A sub-component with its own styles lives in `<F>/<Sub>/` with its own `index.js` and `Styled<Sub>.js` | manual |
| No `assets/`, image files or export leftovers. `field-report.md` may stay beside the component as a helper you delete later. It is not git-ignored [33 MB of unused PNGs in ImageGrid] | `no-assets`, `field-report-staged` |
| Line endings match the repo (`profile.eol`; jaecoo, luxury-trade and omoda use CRLF) | `eol` |

## Props and data

| Item | Check |
|---|---|
| `Client<F>` renders `<Styled<F> id={order}>`. `order` is never a fragment field | `no-page-fields` |
| No fragment field holds breadcrumbs, SEO or meta, the page title, section order, or model or site context. They come from `rootData` (the profile's `breadcrumbs` expression) or a sibling query in `Server<F>.js` [9a7ff2cc: "Breadcrumb is not a field"] | `no-page-fields` |
| Flat fields stay flat. No wrapper group unless the design repeats it [9a7ff2cc: "The header is not needed"] | manual |
| Breadcrumbs, when the design shows them, use the profile's `breadcrumbs` expression, and the row renders nothing when the list is empty | manual |
| `theme.mixins.layout` and `...Layout` appear only when the theme registers a `layout` mixin (`profile.theme.mixins`; ora does not) | `mixins-layout` |
| A fixed-slot design sets repeater min = max = N in the field report, or renders only the rows that exist | manual |

## Fragment

| Item | Check |
|---|---|
| `fragment <F> on FieldsFlexible<F>Layout`, or `EnFieldsEnFlexible<F>Layout` on an English-only site | `folder-name` |
| Media use the shared spreads named in `profile.fragments`, never a hand-expanded `node { mediaItemUrl ... }` tree: `backgroundFields` for image or video, `responsiveMedia` for a desktop and mobile pair, `mediaItem` directly on the ACF image field (its body already has `node`). `node { ...MediaItem }` fails [9a7ff2cc] | `no-hand-media`, wp-graphql `check-fragment` |
| `MediaItemNew` and `ResponsiveMediaItemNew` only when the component reads `src` and `alt` | manual |
| Every spread name exists in the repo. An unknown name silently becomes `__typename` | `spreads-exist` |
| Field names come from the live group (`section <F> --refresh`), not from Figma layer names [9a7ff2cc] | wp-graphql `diff-group` |

## Layout and styles

| Item | Check |
|---|---|
| The section fits the page: root `width: 100%` with `max-width` at the design width, row children shrink (`flex: W 1 0; max-width: Wpx; min-width: 0`), no fixed root height. At 1920, 1440 and 1100 the page has no horizontal overflow [e5857f2a] | verify |
| Row order on screen matches Figma, with Hebrew text still right to left [0636017a] | `no-root-direction`, verify |
| Sibling cards of the same kind share one hover rule. Per-card values are custom properties [ccca3c08] | manual |
| No border that Figma does not show [ccca3c08, 0636017a] | manual (figma-cli drops them) |
| No content wholly outside a clipping parent, and no duplicated rule blocks [ccca3c08] | manual (figma-cli drops it) |
| Class names describe roles (`card`, `card-title`, `card-text`), not layer slugs (`heading-english-7`) | manual |
| No `font-family` literal. Fonts come from `theme.fonts.*` or the page font [57288d61: `SimplerPro_V3` is not in the repo] | `no-font-literal` |
| Colors that equal a `theme.colors` value use the token | `theme-colors` (warn) |
| The root does not set `direction: rtl` unless every row resets it to `ltr` | `no-root-direction` |
| `cursor: pointer` only where there is a link or a handler | manual |

## Mobile

The rules are in [mobile-patterns.md](mobile-patterns.md). These rows are what `check_section.py` enforces.

| Item | Check |
|---|---|
| Media queries use `theme.bps` keys. No literal `@media (max-width: 1279px)` or similar | `no-hardcoded-bp` |
| The section uses `bps.desktop` in a repo whose profile warns that `bps.mobile` and `bps.desktop` overlap (ora at 1279) | `bps-overlap` (warn) |
| `bps.mobile` blocks sit inside the selector they override. A root-level block with many descendant selectors warns unless the record gives the specificity reason | `mobile-nested` (warn) |
| A `:hover` that reveals content sits inside the repo's hover gate (`profile.mobile.hoverGate`). Fails after a mobile pass, warns before one | `hover-gated` |

## propTypes and lint

| Item | Check |
|---|---|
| Every component with props declares `propTypes` (`react/prop-types` is an error in every repo) | `prop-types` |
| ESLint passes on the folder. A repo whose ESLint config cannot load (ora on Next 16) gives a warning, not a pass | `eslint` |

## Field report (when kept)

| Item | Check |
|---|---|
| The report starts with the first WordPress step. Tool output appears only in a closing evidence block | manual |
| Every field block gives Field Label, Field Name, Field Type, its settings, Show in GraphQL and GraphQL Field Name [2e224496] | manual |
| A new section group is titled `section: <name>` and saved before the layout's Clone step points at it [2e224496] | manual |
