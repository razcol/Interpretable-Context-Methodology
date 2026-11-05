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

### Class map

Whenever this pass renames or restructures scaffold classes in the repo, write `stages/04-conform-bind/output/<D>/class-map.json`, one entry per changed class: `{ "<scaffold class>": "<repo selector>" }`. On OND-7 that is `"card-2": ".grid-card.slot-tall-end"` and `"card-title-3": ".card-title"`. A later mobile pass passes the file to figma-cli `--class-map`, so its map finds the renamed targets. No renamed class, no file.

## resync: merge drift

The section is already bound. The new scaffold is the design truth for structure and styles, and the existing files are the truth for data and logic.

1. Diff the new `Styled<Folder>.js` against the existing one. Apply changed values, added and removed rules, and order changes. Keep rules the user added by hand (media queries, `theme.bps` blocks, overrides) and every rule from a mobile pass (the export record's `pair:` line names it) unless Figma removed the element they style.
2. Diff the new client markup against the existing one, matching elements by class name. Apply added, removed and moved elements. Keep every binding expression, `.map`, condition and component from the existing file.
3. Do not touch the `.gql` or `Server<Folder>.js` unless the design added content that needs a new field. Then stop and run `sync` instead.
4. List every applied change in the record. Nothing changed is a valid result. When the record has `pair: <M>`, end with the reminder: "mobile pass M may need `resync --mobile`".

## element: restyle a control

1. Find the control's nodes in `inspect.txt`: fill, stroke weight and align, radius, font, hover and press changes.
2. Edit only the target file and the styled block it owns. Use theme colors and fonts that match, and keep the control's props and handlers.
3. Hover and press come from the inspect lines that name the variant the control changes to.
4. With `--mobile`, change only rules inside `bps.mobile` blocks of the target file.

## mobile: overlay

The run is M (`viewport: mobile`) and the section is already built from D. The mobile frame is the truth for mobile values, and the existing files are the truth for everything else. How a mobile rule is written is in `skills/next-section-repo/references/mobile-patterns.md`. This section says what to apply and in what order.

Inputs, all in `stages/01-export/output/<M>/`:

- `viewport-map.md`, as you edited it at the 01m checkpoint (`viewport-map.json` carries the same edits). The `desktop target` column names the repo selector for each row.
- `mobile-overlay.json`: per target selector, the decls, `hide`, order hints, decor and `touch`.
- `mobile-overlay.styled.txt`: per target selector, the ready `${({ theme }) => theme.bps?.mobile} { ... }` block with the deltas.

Before the first write, copy `Styled<Folder>.js` and `Client<Folder>.js` to `stages/04-conform-bind/output/<M>/before/`. The desktop-frozen audit diffs against these copies. When the export record says `baseline: from-head <sha>`, also check that the repo HEAD is that sha and `git status` shows no change in the section folder, so 05m can rebuild the baseline from it. Stop and say so if either fails.

Rules:

1. **Desktop is frozen.** No declaration outside a `bps.mobile` block changes. The exceptions are gating an existing `:hover` (rule 5) and the base `display: none` of an element added for mobile (rule 4).
2. **Overlay values, not structure.** Nest each block from `mobile-overlay.styled.txt` inside the existing selector the map names as its target. Never copy the mobile scaffold's structure or class names. When the target selector already has a `bps.mobile` block, merge into it.
3. **Order without new markup.** For `moved` rows use CSS first: `order`, `grid-template-areas`, or `display: contents` on a wrapper. Change JSX only when CSS cannot express the order, and say why in the record. The root stays `ltr` (`section-shape.md`). A mobile grid that reads right to left sets `direction: rtl` on that grid.
4. **Hidden and decor.** `hidden-on-mobile`: hide it as in mobile-patterns.md "Hiding and showing". `mobile-only-decor`: search the repo's icons first (mobile-patterns.md "Icons"), present the candidates at the checkpoint, then add the element and hide it outside mobile.
5. **Touch as the frame shows it.** A row with `touch.source=design` gets the tap toggle on `touch.trigger` with no question (recipe and gate: mobile-patterns.md "Hover and touch"). On OND-7 the trigger is the whole card and the chevron is the affordance. Only a row with `touch.source=checkpoint` asks: tap toggle, always shown, or hidden. Apply only the chosen option.
6. **`useIsMobile` only for content swaps** (mobile-patterns.md "`useIsMobile`"), imported from the profile's `mobile.hook`, first entry.
7. **Specificity.** Nest as in mobile-patterns.md "Where mobile rules go". The record says why for each trailing root-level block.
8. **No fields.** A `new-content` row should have stopped the run in 01m. If one shows up here, stop the same way: the group needs a field, and the route is `sync <Folder> <desktop-url> <repo> --mobile <mobile-url>`. Never touch the `.gql` or `Server<Folder>.js`.

On `resync --mobile` (drift mode), apply only what differs between the new overlay and the existing `bps.mobile` rules, under the same rules. Desktop rules and desktop drift are out of scope.

Checkpoint at step 5: the drift list per map row (selector, what changes, rule used), the `touch.source=checkpoint` rows with the three options, and the icon candidates for each decor row. Rows with `touch.source=design` are listed as applied, not asked.

Then run `check_section.py` with `--mobile-pass`, so `no-hardcoded-bp`, `bps-overlap`, `mobile-nested` and `hover-gated` run at their mobile-pass severity.

Audit (mobile):

| Check | Pass condition |
|---|---|
| Desktop frozen | `git diff --no-index` of `output/<M>/before/` against the section files shows changes only inside `bps.mobile` blocks, plus the recorded hover gates |
| Nesting | Every mobile rule is nested, or the record gives the reason for each trailing block |
| Touch | Every hover reveal has its touch path: `design` from the overlay, or the recorded checkpoint decision |
| Icons | Every new icon lists the repo candidates that were rejected. No SVG was drawn before you said none fits |
| Untouched | `.gql` and `Server<Folder>.js` unchanged |
| Checker | `check_section.py --mobile-pass` reports no `fail` on a file this pass changed. A `fail` on a file it may not touch (the `.gql`, `Server<Folder>.js`) that also fails on the `before/` state is listed in the record as pre-existing. Warnings are listed too |

## Record

`conform-record.md` lists every file written or changed, the binding table (field, prop, where it renders) or the drift list, and the `check_section.py` summary with each warning.

On a mobile pass, `stages/04-conform-bind/output/<M>/conform-record.md` holds instead:

- pair: `<D>`
- rows applied: map row, target selector, what changed
- touch: per reveal, the trigger and the source (`design`, or your checkpoint decision)
- icons: per decor row, the candidates, the one used or "new SVG, none fit"
- specificity: each trailing block and why
- check_section: the `--mobile-pass` summary with each warning
