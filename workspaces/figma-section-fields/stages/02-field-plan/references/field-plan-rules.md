# Field plan rules

Which content in the design becomes an ACF field, and in which shape. Field shapes come from the live schema (`patterns`, `section`) of the repo in the export record. Never from another site, and never from the Figma layer names.

## Never a field

These come from the page or the theme, not from the section's group:

- Breadcrumbs. The Server component reads them from its `rootData` prop (`rootData.SEO.breadcrumbs`, falling back to `rootData.breadcrumbs`). A breadcrumb row in the design is rendered from that, and renders nothing when the list is empty.
- SEO and meta, the page title, the model or site name used as context.
- The section order. `order` is a prop the page passes.
- Margins and padding. Editor-controlled spacing is `...Layout` and only when `patterns.counts.spacing` is above 0.

## Shape the fields the way the repo does

- **Flat by default.** A heading, an intro and a disclaimer are separate top-level fields (`intro`, `disclaimer`). Add a group only when the design repeats that group. No `header` wrapper.
- **Names.** Short camelCase names for what the editor changes: `intro`, `grid`, `title`, `text`, `media`, `link`, `disclaimer`. On `sync` the names already in `tree` win, as saved.
- **Repeated cards** are one repeater. A design with a fixed number of slots (three tall cards, three squares) sets repeater min = max = that number, and says so in the plan. A design whose card kinds differ uses one repeater per kind, or a select field for the kind; say which in the questions.
- **Pictures.** Image or video: `responsiveFull`, a Clone of the `BackgroundFields` group (`profile.fragments.backgroundFields`). A desktop and mobile pair: `responsiveMedia`. A single image: `mediaItem`, an Image field. A hover picture is a second field of the same shape, not `desktop` and `mobile` inside one field.
- **Buttons.** One button is a group with a Seamless Clone of the button group (`profile.fragments.button`, `Button` or `ButtonItem`). Several buttons are a repeater with the Clone on the row.
- **Text.** Plain text is Text. A paragraph with line breaks is Text Area. Rich text is WYSIWYG only when the design has links or bold inside the text.
- Use the shape and clone source `patterns.examples` shows for each kind. When an example key is absent, use the shapes above. Do not open another section's `.gql`.

## Questions the plan must ask

Ask only those that apply:

- Text that appears only on hover: does it also show on touch screens, or is it hidden there?
- Cards or tiles: is each one a link? If yes, add a `link` field (Link type) per card.
- A fixed slot count: are the slots fixed at that number?
- A picture: can it be a video too?
- The folder name: is `<Folder>` the Layout Name you will type in ACF?

## Folder name

The folder name is the ACF Layout Name, exact case. The fragment is `fragment <Folder> on FieldsFlexible<Folder>Layout`. `<graphqlName>` is the folder name with its first character lowercased. The name has no `Server` and is not a global fragment name in the profile, because a section fragment with that name would replace the shared one site-wide.
