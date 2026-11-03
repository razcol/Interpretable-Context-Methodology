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
| `theme.mixins` | string[] | Keys of `theme.mixins`, for example `["buttons"]` or `["layout", "flexCenter"]` |
| `theme.bps` | string[] | Keys of `theme.bps` |
| `theme.colors` | object | Flattened color path to normalized value, for example `{"primaryBlue": "#1e6679", "table.header": "#b4d0de"}`. Hex is lowercase 6 or 8 digits. `rgba()` becomes `#rrggbbaa` |
| `theme.fonts` | `[{export, files[]}]` | Each `localFont` export name and the base names of its `src` files without extension |
| `eol` | `"lf"` or `"crlf"` | Majority line ending of `sectionsDir/*/*.js` |
| `eslint` | `{schemaPath, propTypes}` | GraphQL schema path and the `react/prop-types` level from `.eslintrc.js` |
| `lintCommand` | string[] | Argument list that lints a folder, for example `["npx", "eslint"]` |
| `breadcrumbs` | string or null | Source expression the repo uses, for example `rootData?.breadcrumbs` |
| `useWP` | boolean | Whether the repo has its own `app/hooks/useWP.js` (WordPress menu and data hooks) |
| `pageDirection` | `"rtl"`, `"ltr"` or null | `direction` set in GlobalStyle |
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

## Warnings

The probe adds a warning, and still succeeds, when:

- `installed` differs from `declared` for `next` or `runtime` (major or minor).
- `ccTemplates/section.js` uses `theme.mixins.layout` but `layout` is not in `theme.mixins`.
- A file it needs is missing.
- `lint` in `package.json` is `next lint` and Next 16 or later is declared.
