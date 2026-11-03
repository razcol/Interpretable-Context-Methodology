# Binding rules

How the staged scaffold becomes the bound section, per route. What a finished section looks like is in `skills/next-section-repo/references/section-shape.md`.

## new and sync: bind

The fragment arrives on the Server component's props under the field names it selects, next to `layout`, `order` and `rootData` (see `ServerCtaBoxBlurSection.js` in ora).

- `Server<Folder>.js` reads the fragment fields from `props` and maps them to the client props the scaffold declared. Data shaping happens here: picking `media.imageFields.desktop` for an image, mapping a repeater to an array of card props.
- `Client<Folder>.js` keeps the scaffold's markup and class names. Each content prop is now required data: remove its Figma default when a field provides it. Keep a default only for text no field provides, and say why in the record.
- Repeated cards become a `.map` over the repeater, with the card markup from the first scaffold card. Cards whose markup differs (tall and square) map over their own list or branch on a field.
- Images: a `responsiveFull` or `responsiveMedia` field is rendered with the repo's own media component (for example `MediaBackground` or `ResponsiveImage` under `UIComponents`) when the scaffold used a background image. Otherwise set the scaffold's CSS image variable from the field's URL.
- Buttons and links use the repo's button component with the spread object as is. Do not flatten it.
- propTypes describe the bound shapes. Reuse the repo's shared propTypes (for example `app/utils/generalPropTypes`) when it has them.
- `order` and `layout` keep flowing from Server to Client. `$layout={layout}` only when the profile registers a layout mixin.
- Breadcrumbs, when the design shows them, come from the `rootData` prop the Server component receives: `rootData.SEO.breadcrumbs`, falling back to `rootData.breadcrumbs` (the hand-fixed ora `ImageGrid` does this). The profile's `breadcrumbs` value shows which form the repo already uses. Render nothing when the list is empty.
- Do not rename classes to match field names. Do not add a field group, PHP or `acf-json` to the repo.
- Mount the section only where the user already said. Flexible sections render from WordPress, so usually there is nothing to mount.

## resync: merge drift

The section is already bound. The new scaffold is the design truth for structure and styles, and the existing files are the truth for data and logic.

1. Diff the new `Styled<Folder>.js` against the existing one. Apply changed values, added and removed rules, and order changes. Keep rules the user added by hand (media queries, `theme.bps` blocks, overrides) unless Figma removed the element they style.
2. Diff the new client markup against the existing one, matching elements by class name. Apply added, removed and moved elements. Keep every binding expression, `.map`, condition and component from the existing file.
3. Do not touch the `.gql` or `Server<Folder>.js` unless the design added content that needs a new field. Then stop and run `sync` instead.
4. List every applied change in the record. Nothing changed is a valid result.

## element: restyle a control

1. Find the control's nodes in `inspect.txt`: fill, stroke weight and align, radius, font, hover and press changes.
2. Edit only the target file and the styled block it owns. Use theme colors and fonts that match, and keep the control's props and handlers.
3. Hover and press come from the inspect lines that name the variant the control changes to.

## Record

`conform-record.md` lists every file written or changed, the binding table (field, prop, where it renders) or the drift list, and the `check_section.py` summary with each warning.
