# Migration rules

Bind each field in the confirmed fragment to the JSX. The Styled component stays the visual shell.

## Props

Replace hardcoded text and image `src` values from the Figma export with props that match the fragment.

Do not rename styled classes to match field names.

Keep `index.js` as the default export.

`order` is not a field.

## Images and buttons

Bind the selection in the `.gql`. A field that spreads `BackgroundFields`, `ResponsiveMediaItem`, `MediaItem`, or `Button` is passed through as that object. Do not flatten a group into one image URL unless the fragment selects `node.mediaItemUrl` itself.

## Render location

If the user already gave a render location, wire the component only there and record the path in `output/migration-record.md`.

If they did not give a render location, stop. Do not ask where to render. Do not add a mount.

## Record

`output/migration-record.md` lists every file changed and each field binding. A fragment field the component does not read is listed as unused with a reason.
