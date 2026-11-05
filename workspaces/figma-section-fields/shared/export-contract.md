# Export contract

What this workspace relies on from `tools/figma-cli`. `$FIGMA` is the call in `shared/figma-cli-setup.md`. `$FIGMA help` prints every flag.

## Commands this workspace runs

| Command | Stage | Writes |
|---|---|---|
| `$FIGMA inspect '<url>'` | 01 | stdout: per node its box, flow (in flow, absolute inside auto-layout, free), sizing per axis (fixed, hug, fill), auto-layout, clipping, fills, stroke weight and align, font, and the variant each hover changes to. Tap (ON_CLICK) reactions show only in the viewport map's `interaction` column |
| `$FIGMA render '<url>' --out <file>.png --scale 1` | 01 | Figma's own PNG of the node, the Level 1 reference |
| `$FIGMA export '<url>' --out <file>.html` | 01 | HTML preview at Figma's pixel sizes |
| `$FIGMA export '<url>' --out <file>.html --fluid` | 05 | HTML preview with the scaffold's fluid sizing |
| `$FIGMA export '<url>' --dist <dir> --scaffold next-section --component <Folder> --repo-profile <profile.json> --section-map <file.json> [--font-map 'Family=export']` | 01 | `<dir>/<Folder>/` in the repo's shape, and the section map (one row per classed layer, outside `<dir>/<Folder>/`) |
| `$FIGMA export '<url>' --dump <file>.json` | 01 | The raw Figma nodes response, for a paired desktop or mobile frame |
| `$FIGMA export '<M url>' --mobile-of <D section-map.json> --overlay-out <dir> --repo-profile <profile.json> [--section-dir <dir>] [--class-map <json>] [--map <viewport-map.json>] [--font-map …]` | 01m | Into `<dir>` only: `section-map.json` (mobile), `viewport-map.json`, `viewport-map.md`, `mobile-overlay.json`, `mobile-overlay.styled.txt`. Never writes the repo |

Use `--name LAYER` or `--exclude LAYER [--index N]` only when the user asks. `--fixed` keeps pixel sizes and is only for a pixel comparison the user asks for. `--assets` is never used: images come from WordPress.

## What the scaffold writes

The files in the profile's `scaffold.files`, except the `.gql` (stage 03 writes it):

- `index.js` re-exports `./Server<Folder>`.
- `Server<Folder>.js` starts with `import 'server-only';` and passes `layout`, `order` and the content props.
- `Client<Folder>.js` starts with `'use client';`, takes every text and image as a prop (text keeps the Figma text as its default), and declares propTypes.
- `Styled<Folder>.js`: one `styled.div` with role class names (`card`, `card-title`, `card-media`).

Images are props with no URL written. Background images are CSS variables set from props (`--card-image`). Sibling cards that hover the same way share one hover rule. The root is fluid up to the Figma width, with no breakpoints: mobile rules come only from the mobile mode's overlay. Colors and fonts that exist in the repo theme become theme tokens. Line endings follow the profile.

## Notes on stderr

`note:` lines say where the output could not follow Figma exactly. Copy every one into the export record.

| Note | Meaning |
|---|---|
| `hairline-dropped <id>` | A 1px or thinner stroke on an image frame was dropped, because Figma shows it as no border. `--keep-hairlines` keeps it |
| `hover-size-skipped <id>` | A hug or fill size changes on hover and is not animated |
| `font-unmatched <family>` | No theme font matched. Ask which export to use, then rerun with `--font-map` |
| `scaffold-image-dropped` | An image paint could not become a prop |

## Exit codes

| Code | Meaning | Do |
|---|---|---|
| 0 | Done | Continue |
| 2 | Usage | Fix the arguments |
| 3 | Token rejected | Stop. Ask the user to check `/home/dev/cli/figma-cli/.env` |
| 4 | No such node | Stop. For a layer inside an instance, export the instance id with `--name` |
| 5 | `rate-limited`: Figma rate limited the request | Retry once after a wait, then stop |
| 6 | Bad `--index` or bad document | Stop |
| 7 | `missing-asset`: Figma returned no image for a node | Stop. Say which node |
| 8 | Network or HTTP failure | Retry once, then stop |
| 9 | `--name` matched nothing | Checkpoint: show the listed children |
| 10 | `--name` matched several layers | Checkpoint: show the paths |
| 11 | Mobile mode: the mobile frame adds content (`new-content` rows) | Stop. The group needs a field: `sync <Folder> <desktop-url> <repo> --mobile <mobile-url>` |
| 12 | Mobile mode: `unmatched` or `target-missing` rows | Checkpoint on `viewport-map.md`, then rerun with `--map` (`stages/01-export/references/viewport-map.md`) |

In mobile mode the files are written on 0, 11 and 12, and the last stdout line is the `--overlay-out` path.
