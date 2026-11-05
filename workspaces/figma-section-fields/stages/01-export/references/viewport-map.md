# Viewport map

How to read and edit the map figma-cli writes in mobile mode (`export --mobile-of`). It pairs every node of the mobile frame M with a target in the built desktop section D. figma-cli writes two files in `stages/01-export/output/<M>/`: `viewport-map.md`, the edit surface you show the user, and `viewport-map.json`, what `--map` reads. Flags and exit codes: `shared/export-contract.md`.

## Columns

| Column | Meaning |
|---|---|
| `id` | Row id. The same in the `.md` and the `.json` |
| `mobile node` | Name and node id in M. Empty on a `hidden-on-mobile` row |
| `desktop target` | Repo selector in the section (`.grid-card.slot-tall-end`), or the node in D |
| `status` | One of the statuses below |
| `signal` | The match signal that paired the row, or `user` after your edit |
| `order m/d` | Visual index among siblings in M, and in D |
| `box` | Mobile width × height and sizing (fixed, hug, fill) |
| `deltas` | What differs from D: font size, line height, letter spacing, padding, gap, radius, fill, shadow, direction |
| `interaction` | D's hover variant, M's affordance, and the touch source (`design` or `checkpoint`) |

## Statuses

| Status | Meaning | Exit |
|---|---|---|
| `same` | Matched. Restyle only | 0 |
| `moved` | Matched, and the order changes | 0 |
| `hidden-on-mobile` | In D, not in M | 0 |
| `mobile-only-decor` | A small vector or image in a matched card with no desktop counterpart (icon, divider). No field. Carries an `affordance: chevron, arrow or plus` guess | 0 |
| `new-content` | Content in M that no field holds. The run stops | 11 |
| `unmatched` | No signal paired the node | 5 |
| `target-missing` | Matched, but the target class is not in the repo's `Styled<Folder>.js` or `Client<Folder>.js` | 5 |

## Match signals, strongest first

1. Equal normalized text: trimmed, whitespace collapsed, Hebrew niqqud stripped. OND-7 matched its cards by title.
2. The same `imageRef` on an image fill. The same WordPress image is usually placed in both frames.
3. Instances of the same component or component set (variants `Property 1=Default` and `Variant2`).
4. Descendants: a container whose matched children point into the same desktop container.
5. The same layer name and the same order among siblings. Weak, because names like `Frame 1562162393` repeat.

The matcher never guesses. No signal, or a tie it cannot split by order (repeated labels such as "לפרטים נוספים"), gives `unmatched`.

## Target resolution

A matched row's desktop class resolves to a repo selector in this order:

1. `--class-map`: the scaffold class to repo selector map desktop 04 writes to `stages/04-conform-bind/output/<D>/class-map.json`.
2. The class itself.
3. The class without its `-<n>` suffix (`card-2` to `card`).

When none occurs in the repo files, the row is `target-missing`. Desktop 04 often renames classes: on OND-7 scaffold `card-2` became `.grid-card.slot-tall-end`.

## Interaction and touch

Only for rows whose desktop target reveals content on hover.

- `design`: the mobile node has a prototype tap (an `ON_CLICK` change-to an expanded variant), or a disclosure affordance (chevron, arrow, plus). The trigger is the node with the reaction, else the affordance's nearest matched card. 04m applies it with no question.
- `checkpoint`: the frame shows neither. 04m asks the user.

## Editing at the exit 5 checkpoint

Show the user the `unmatched` and `target-missing` rows. They may edit three columns, and nothing else:

- `desktop target`: the repo selector the node belongs to.
- `status`: for example `mobile-only-decor`, `hidden-on-mobile`, or `new-content` (which stops the run with exit 11 on rerun).
- `touch` (in `interaction`): `design` with the trigger, or `checkpoint`.

For a `target-missing` row the usual fix is a class-map entry, scaffold class to repo selector, written to `stages/04-conform-bind/output/<D>/class-map.json`. Create the file when it is absent.

Then carry each edited row into `viewport-map.json` by `id`, and rerun with `--map stages/01-export/output/<M>/viewport-map.json` and `--class-map`. Your edits win over the matcher, and the row's `signal` becomes `user`. figma-cli recomputes `box`, `deltas` and `order` from the frame, so never edit them, or the overlay files, by hand.
