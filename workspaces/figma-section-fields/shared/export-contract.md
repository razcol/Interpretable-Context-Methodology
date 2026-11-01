# Export contract

The exporter is the executable `tools/figma-cli`. This file is the contract this workspace relies on. `tools/figma-cli help` prints the same flags.

## Command

From `workspaces/figma-section-fields`:

```
tools/figma-cli export <file-or-url> [node-id] --dist <export-dir>
```

Always pass `--dist`. This workspace does not use `--stdout` or `--dump`. Pass `--name` or `--exclude` only when the user asked. A figma.com design URL may include `?node-id=`. That id is the node, and a second node id must match it. A file key still needs a node id.

`tools/figma-cli inspect <file-or-url> [node-id]` prints fills, type, stroke, radius, and hover or press color and opacity changes. It writes no component. Use it when adjusting an existing control, not when exporting a section.

Needs Node >= 20. The token is the environment variable `FIGMA_ACCESS_TOKEN`. Never write the token into a file.

## Flags this workspace uses

`--name LAYER` exports the descendant with that exact, case-sensitive name, children included. The fetched node's own name is not a match. One match becomes the document root. Several matches list each path and exit 10 when there is no terminal. No match exits 9.

`--exclude LAYER` drops every visible direct child of the export root with that exact name, children included. A deeper layer of that name stays. The export root stays even when its name is listed. A name that matches nothing is ignored. Repeat the flag for each name. Several direct children with the same name are all omitted.

`--exclude LAYER --index N` drops only that direct child. `N` is the 1-based slot in that node's `children` array. The child at that slot must have the given name. A missing slot or a different name exits 6.

`--assets <dir>` with `--dist` downloads images and rewrites paths relative to the component `.js` file. Without `--assets`, image URLs stay remote and expire.

Failures start with `error: <kind>` on stderr, then a sentence. Exit 9 lists child names and ids. Exit 10 lists each path and id. Exit 4 on a node id that is not an instance id says to export the instance and pass `--name`.

## Files on disk

The folder name is PascalCase: `<export-dir>/<PascalCaseName>/`.

- `index.js`
- `<Name>.js`
- `Styled<Name>.js`
- `assets/` only when `--assets` was passed. The CLI does not create that folder by itself

Stage 02 adds `<Name>.gql` and `field-report.md` in that same folder. The CLI does not write those two files. `field-report.md` is the WordPress dashboard checklist for this section. It is not written under `stages/02-section-graphql/output/`.

## Exit codes

| Code | Meaning |
|------|---------|
| 2 | Usage error |
| 6 | Bad exclude index |
| 9 | No layer matched the name |
| 10 | More than one layer with the same name |

Exit 9 and exit 10 wait for a human to pick a path. Any other failure stops the run. Do not invent a component folder.
