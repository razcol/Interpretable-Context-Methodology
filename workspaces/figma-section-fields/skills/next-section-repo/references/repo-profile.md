# Repo profile

`scripts/probe_repo.py` writes one JSON object that describes a Next.js section repo. `figma-cli --scaffold next-section --repo-profile <file>` and `scripts/check_section.py --profile <file>` read it. This file is the only definition of its shape.

The probe reads repo files as text. It never imports, requires or runs repo code.

## Envelope

```json
{ "ok": true, "profile": { "schemaVersion": 1, "...": "..." }, "warnings": ["..."] }
```

A reader rejects any `schemaVersion` other than `1`. `--out <file>` writes only the `profile` object to that file.

## Keys

| Key | Type | Meaning |
|---|---|---|
| `schemaVersion` | `1` | Shape version |
| `appRoot` | string | Absolute path of the Next app root (the folder with `package.json` and `app/`) |
| `next` | `{declared, installed}` | Versions from `package.json` and `node_modules/next/package.json`. `installed` is null when absent |
| `runtime` | `{declared, installed}` | The same for `@colmobil/next` |
| `sectionsDir` | string | Path of the sections folder, relative to `appRoot` (usually `app/components/Sections`) |
| `existingSections` | string[] | Folder names already in `sectionsDir` |
| `globalFragmentDirs` | string[] | Folders passed to `globalFragments` in `app/core.config.js`, relative to `appRoot` |
| `fragments` | object | Fragment names by role. See below |
| `scaffold.files` | string[] | Files `ccTemplates/section.js` writes, with `{F}` for the folder name, for example `index.js`, `Server{F}.js`, `Client{F}.js`, `Styled{F}.js`, `{F}.gql` |
| `theme.mixins` | string[] | Keys of `mixins` on the theme passed to `ThemeProvider`, for example `["buttons"]` or `["layout", "flexCenter"]`. A mixin file the theme does not register is not listed (ora has `layoutMixins.js`, but its theme has only `buttons`) |
| `theme.bps` | string[] | Keys of `theme.bps` |
| `theme.bpsMedia` | object | Each `bps` key to its media string with `${breakPoints.x}` replaced and spaces collapsed, for example `{"mobile": "@media (max-width: 1279px)"}`. A key whose value is not a string (ora `mobilePixels`) is null |
| `theme.breakpoints` | object | Numbers of the object the `bps` strings interpolate (ora `{"mobile": 1279, "smallerMobile": 320, "laptop": 900}`). Empty when the strings are literal |
| `theme.layoutHeights` | string[] | Keys of `layoutHeights` on the `ThemeProvider` theme. ora has `header` but no `mobileHeader`. Use only a listed key |
| `theme.colors` | object | Flattened color path to normalized value, for example `{"primaryBlue": "#1e6679", "table.header": "#b4d0de"}`. Hex is lowercase 6 or 8 digits. `rgba()` becomes `#rrggbbaa` |
| `theme.fonts` | `[{export, files[]}]` | Each `localFont` export name and the base names of its `src` files without extension |
| `eol` | `"lf"` or `"crlf"` | Majority line ending of `sectionsDir/*/*.js` |
| `eslint` | `{schemaPath, propTypes}` | GraphQL schema path and the `react/prop-types` level from `.eslintrc.js` |
| `lintCommand` | string[] | Argument list that lints a folder, for example `["npx", "eslint"]` |
| `breadcrumbs` | string or null | Source expression the repo uses, for example `rootData?.breadcrumbs` |
| `useWP` | boolean | Whether the repo has its own `app/hooks/useWP.js` (WordPress menu and data hooks) |
| `pageDirection` | `"rtl"`, `"ltr"` or null | `direction` set in GlobalStyle |
| `mobile` | object | How the repo handles mobile. See below |
| `dev` | `{script, port}` | The `dev` script text and its port (3000 unless `-p` or `PORT` sets one) |
| `browser` | string or null | Chrome or Chromium path for verify |

## `fragments`

Each value is `{name, path}` with `path` relative to `appRoot`, or null when the repo has none.

| Role | Matches fragment name (case-insensitive) |
|---|---|
| `button` | `Button`, `ButtonItem` |
| `mediaItem` | `MediaItem` |
| `mediaItemNew` | `MediaItemNew` |
| `responsiveMedia` | `ResponsiveMediaItem` |
| `responsiveMediaNew` | `ResponsiveMediaItemNew` |
| `backgroundFields` | `BackgroundFields`, searched under all of `app/components` |
| `layout` | `Layout` |
| `seo` | `Seo` |

`name` is the name inside the `fragment` line, not the file name. ora's `mediaItem.gql` defines `MediaItem`.

## Theme source

The theme is the object passed to `<ThemeProvider theme={x}>` in `app/` (files nearest `app/` first), followed through its import. Specifiers resolve relative, `@/` to `app/components`, and others to `app/` (the jsconfig `baseUrl`). With no `ThemeProvider`, the default export of `app/styles/theme/index.js` is used.

## `mobile`

| Key | Type | Meaning |
|---|---|---|
| `hook` | `[{import, count}]` | Each source `useIsMobile` is imported from in `app/`, most used first. Relative imports are counted under their `app/`-relative path, so `../../hooks/useIsMobile` counts as `hooks/useIsMobile`. In a new section, use the first |
| `responsiveImage` | string or null | Path of `ResponsiveImage.js` (or `ResponsiveImage/index.js`), `Core/` first, for example `app/components/Core/Image/ResponsiveImage.js` |
| `hoverGate` | `"hover-media"`, `"bps-desktop"` or null | `hover-media` when a section `Styled*.js` uses `@media (hover: hover)`. Otherwise `bps-desktop` when a section has a `:hover` inside a `bps.desktop` block. Null when sections gate no hover, and then gate with `bps.desktop` |
| `icons` | `{publicIcons, inline[]}` | `publicIcons` is `"public/icons"` when that folder exists, else null. `inline` lists folders that hold `*Icon*.js` files drawing an `<svg>`. Search both before drawing a new icon |

All paths are relative to `appRoot`.

## Checks that read the profile

`check_section.py` adds these rows. `--mobile-pass` makes `hover-gated` fail instead of warn.

| Id | Status | Rule |
|---|---|---|
| `bps-overlap` | warn | `theme.bpsMedia` desktop and mobile ranges overlap, and a section `Styled*.js` uses `bps.desktop` |
| `mobile-nested` | warn | A root-level `bps.mobile` block holds more than 6 nested selectors |
| `hover-gated` | warn, fail with `--mobile-pass` | A `:hover` rule shows content (`opacity: 1`, `display` other than none, `visibility: visible`, a `max-height` or a `grid-template-rows` track) outside the gate. The gate is `@media (hover: hover)`, plus `bps.desktop` unless `hoverGate` is `hover-media`. A `css` helper counts where it is interpolated |
| `no-hardcoded-bp` | fail | A literal `@media (max-width: Npx)` or `min-width` instead of `theme.bps` |

## Warnings

The probe adds a warning, and still succeeds, when:

- `installed` differs from `declared` for `next` or `runtime` (major or minor).
- `bps.desktop` and `bps.mobile` both match at some width. The text is `bps.desktop and bps.mobile both match at <N>px` (ora: `1279px`). `--out` drops warnings, so readers recompute the overlap from `theme.bpsMedia`.
- `ccTemplates/section.js` uses `theme.mixins.layout` but `layout` is not in `theme.mixins`.
- A file it needs is missing.
- `lint` in `package.json` is `next lint` and Next 16 or later is declared.
