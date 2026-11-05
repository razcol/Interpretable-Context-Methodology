# Plan v2: desktop first, then mobile, in figma-section-fields and figma-cli

Status: implementation in progress. Evidence: `session-extract-2026-11-05-ond-7-mobile.md` (same folder). Target workspace: `workspaces/figma-section-fields/`, plus `/home/dev/cli/figma-cli`. Bracketed ids like [70281275] are agent transcript ids, not commits; the pushed OND-7 mobile commit is `8ccedaa`.

## 1. Goal and scope

Figma keeps the desktop and mobile designs of a section as separate frames with separate node ids. Neither can be derived from the other, so the user has to give the mobile URL. Today the workspace takes one URL per run. On OND-7 the mobile pass had to be improvised by hand (session `70281275`).

The workspace must handle a section in two passes:

1. **Desktop pass**: the current `new` / `sync` / `resync` flow, unchanged in behavior.
2. **Mobile pass**: a second Figma URL, applied to the same section folder as a mobile overlay under `theme.bps.mobile`. Desktop output stays the same.

It must support both entry points:

- **Case A, both URLs known up front**: `new <desktop-url> <repo> --mobile <mobile-url>`. Desktop runs first. The mobile pass follows automatically after desktop stage 05 passes.
- **Case B, mobile later** (the OND-7 case): `mobile <Folder> <mobile-url> <repo>` on a section whose desktop is already built. When no desktop export record exists, the run asks for the desktop URL.

**Scope of figma-cli**: figma-cli gets a light mobile mode (`--section-map` on the desktop scaffold, `export --mobile-of`) that wraps the desktop artifacts and emits only a `bps.mobile` overlay. It reuses the desktop work (no second scaffold into the repo, no asset download, no field logic) and never writes into the repo (section 7, F1-F4).

**Non-goals**

- Deriving a mobile layout from the desktop frame, or the reverse.
- Mobile-first sections, where mobile is the base and desktop the overlay. The recorded `viewport` field leaves room for this later.
- Tablet as its own design. All five repos treat 320–1279px as "mobile" (section 2).

## 2. Mobile pattern map (ora, smart, jaecoo, luxury-trade, omoda)

Measured on 2026-11-05 in the main checkouts: `/home/dev/ora-next/code/app`, `/home/dev/smart-next/code/app`, `/home/dev/jaecoo-next/code/app`, `/home/dev/colmobil-luxury-trade/code/app`, `/home/dev/omoda-next/code/app` (OND-7 worktree: `/home/dev/ora-next/.worktrees/OND-7/code/app`). This section is the draft for the new canonical reference `skills/next-section-repo/references/mobile-patterns.md` (Phase 1, task T6). Per-repo values belong in the probe profile, not in the doc (task T10).

### 2.1 Breakpoints

| Repo | `theme.bps.mobile` | `theme.bps.desktop` | Extra keys | Source |
|---|---|---|---|---|
| ora | `@media (max-width: 1279px)` | `@media (min-width: 1279px)` ⚠ overlaps at 1279 | `laptop` (max-height 900 and min-width 1279), `smallerMobile` (max-width 320), `mobilePixels` | defined inline in `styles/theme/index.js`. `styles/theme/layout.js` has a second `bps` (1279 / 1280) that the theme does not use |
| smart | `screen and (max-width: 1279px)` | `screen and (min-width: 1280px)` | none | `styles/theme/layout.js` |
| jaecoo | same as smart | same as smart | `desktop1440` (it is `max-width: 1440px`, despite the name) | `layout.js` |
| luxury-trade | same as smart | same as smart | `desktop1440` (same as jaecoo) | `layout.js` |
| omoda | same as smart | same as smart | none | `layout.js` |

Rules:

- There is one real breakpoint: 1279/1280. "Mobile" covers phones and tablets (320–1279px). No repo has a `tablet` key.
- CSS is desktop-first. Base rules are desktop, and mobile is the override. Counts in `app/`: `bps.mobile` 274–696 per repo, `bps.desktop` 9–23, raw `@media` 1–11.
- Use only `theme.bps.*` keys, always written as `${({ theme }) => theme.bps?.mobile} { … }`. Never hard-code `1279px`.
- In ora, a rule under `bps.desktop` also applies at exactly 1279px, together with the mobile rules. Verify both 1279 and 1280 (section 6.5).

### 2.2 Where mobile rules go

- In `Styled*.js`, 81–90% of `bps.mobile` blocks sit inside the selector they override (ora 617 blocks, 115 at root; smart 268/43; jaecoo 573/73; luxury-trade 465/65; omoda 649/66). Nearly every section folder has at least one (smart: 25 of 26).
- Pattern:

```js
.card-title {
  font-size: 32px;

  ${({ theme }) => theme.bps?.mobile} {
    font-size: 24px;
  }
}
```

- A single trailing mobile block is acceptable only when nesting cannot win on specificity, for example slot rules like `.grid-card.slot-*` that need the same weight. The record must give the reason (OND-7 used a trailing block without one).
- Values are plain `px` taken from the mobile frame. `vw` is rare (9–31 uses per repo). `!important` appears in mobile font overrides in jaecoo, but do not add new ones unless a nested component wins otherwise.
- The mobile side gutter comes from the mobile frame. It is often 14px (jaecoo sections use `margin: 0 10px` plus `padding: 0 12px`), but never take it from this note.
- ora's ThemeProvider theme (`styles/theme/index.js`) has no `mixins.shrink`, `mixins.layout` or `layoutHeights.mobileHeader`. They live only in `styles/theme/mixins/layoutMixins.js` and `styles/theme/layout.js`. Never assume a theme mixin or layout height exists: the probe reports which ones are present (T10). Where `layoutHeights.mobileHeader` (or `mobileNavbar`) is present, use it for offsets such as `scroll-margin-top`.

### 2.3 JavaScript branching: `useIsMobile`

| Repo | Hook import | Implementation |
|---|---|---|
| ora | `hooks/useIsMobile` (15 imports, one of them relative) and `@colmobil/next/core/hooks/useIsMobile` (24) | local: `react-use` `createBreakpoint(breakPoints)` plus `useEffect`, returns `breakpoint === 'mobile'`. Shared: runtime |
| smart, jaecoo, luxury-trade, omoda | `@colmobil/next/core/hooks/useIsMobile` only | runtime |

Rules:

- Both hooks return `false` on the server and on first paint, so the desktop markup renders first. Use CSS for layout, order, size and visibility. Use `useIsMobile` only when the markup or the content differs: another component, truncated text (ora `LegalNote` read-more), a mobile-only button list (`ModelCtaBanner`), or choosing a mobile media source.
- In a new section, import the hook the repo already uses the most. In ora that is `@colmobil/next/core/hooks/useIsMobile`, which `ResponsiveImage` uses.

### 2.4 Media

- ACF responsive pairs: `imageFields { desktop { ...MediaItem } mobile { ...MediaItem } }` through the `ResponsiveMediaItem` fragment (`fragments/global/responsiveMediaItem.gql`, `ResponsiveImageFieldsItem.gql`).
- `@/Core/Image/ResponsiveImage` picks `mobile` when `isMobile` is true and the mobile image exists, and otherwise falls back to `desktop`. `MediaBackground` passes `imageFields` through to it.
- Background images set from props pick `isMobile ? mobile?.node?.src || desktop?.node?.src : desktop?.node?.src` (jaecoo `FullImageBackground`, `CarBook`).
- Video uses `videoFields.{desktop,mobile}` the same way.
- Spacing comes from `layout.marginBottom.{desktop,mobile}` through the `Layout` fragment and `mixins.layout` or `layoutMargin`, only in repos whose theme registers the mixin (ora does not, see 2.2).
- Field consequence: when the mobile frame crops or composes an image differently from desktop, the field needs a desktop/mobile pair (`responsiveMedia` role in the profile). That decision belongs in stage 02 and is why Case A inspects mobile before the field plan (section 4.1).

### 2.5 Hover on touch screens

- luxury-trade gates hover effects with `@media (hover: hover)` or `(hover: hover) and (pointer: fine)` (`MagazineCard`, `ArticlePreview`, `MediaWithTitle`). jaecoo has 2 such rules. ora, smart and omoda have none.
- The mobile touch path is read from the mobile Figma frame. It is a product requirement, not an agent choice. On OND-7 the mobile frame shows a chevron on each card. Restricting hover to desktop (`bps.desktop` gate) and a chevron tap toggle (`.is-open` from `useState`) came from that design. The whole `.grid-card` carries the `onClick`, and the chevron is the visible affordance (`ClientImageGrid.js` L40-45, `StyledImageGrid.js` L203-209, L407-416).
- Rule: when desktop reveals content on hover and the mobile frame shows a disclosure affordance (chevron, arrow, plus) on that element, implement a tap toggle as the frame shows it, and gate the hover with the repo's gate (luxury-trade: `hover: hover`, others: `bps.desktop`). Only when the frame shows no affordance and no expanded state, stop at a checkpoint with three options: tap toggle, always shown, or hidden (section 6.4).

### 2.6 Hiding and showing elements

- CSS: `display: none` inside a `bps.mobile` (or `bps.desktop`) block. This is the default.
- JS: `{isMobile && …}` or `{!isMobile && …}`, only when the hidden element is heavy or has different content (ora `ColorsViewer`, `LeasingInfoBox`).
- Icons: search the repo before drawing one. Look in `public/icons/*.svg` (imported through `Image`/`ResponsiveImage`) and in inline icon components such as ora `Layout/ContactUs/Assets/Icons/ClockIcon.js`. Present the candidates. Draw a new inline SVG only after the user says none fits [657777ae].

## 3. What broke on OND-7, mapped to changes

| # | Gap (report "Still missing") | Change | Task |
|---|---|---|---|
| 1 | No way to say "this URL is the mobile of that section" | `mobile` trigger, `--mobile` flag, pair records | T1, T2, T3 |
| 2 | Stage 04 resync would treat the mobile frame as the base | `mobile: overlay` rules in `binding-rules.md` | T7 |
| 3 | Stage 05 widths are desktop only, and ora overlaps at 1279 | Mobile verify profile and boundary check | T8, T10 |
| 4 | No mobile pattern reference | `mobile-patterns.md` (section 2) | T6 |
| 5 | Hover-to-touch decided by the agent alone | Touch path read from the mobile frame, checkpoint only when the frame shows none | T7, F3 |
| 6 | Level 2 is impossible without `node_modules` or DB | Promote the esbuild harness to a skill script | T12 |
| 7 | No desktop regression check after the mobile pass | Desktop baseline before, diff after | T8, T12 |
| new | Element mapping desktop ↔ mobile done in the agent's head | Section map, matcher and overlay in figma-cli, `viewport-map.md`/`.json` edit surface | F1, F2, F3 |

## 4. Target flows

### 4.1 Case A: `new <desktop-url> <repo> --mobile <mobile-url>`

```
Desktop pass (key D = desktop node id)
  01 export D, scaffold with --section-map ── also: mobile preflight on M (inspect + render + dump only)
  02 field plan D ── reads M's preflight: responsive image pairs, mobile-only content
     STOP (new): user builds the ACF group, replies `continue D`
  03 fragment D
  04 conform-bind D
  05 verify D (desktop widths) ── on PASS: save desktop baseline shots
        │
        ▼ same run, no extra trigger
Mobile pass (key M = mobile node id, pair: D)
  01m $FIGMA export '<M url>' --mobile-of stages/01-export/output/<D>/section-map.json
        --section-dir <app root>/<sectionsDir>/<Folder> --overlay-out stages/01-export/output/<M>
        --repo-profile stages/01-export/output/<M>/profile.json [--class-map ...] [--font-map ...]
      ── exit 12: CHECKPOINT on the map, rerun with --map stages/01-export/output/<M>/viewport-map.json
  04m overlay under theme.bps.mobile ── CHECKPOINT: drift list, touch only for rows without a design affordance
  05m verify (mobile widths, 1279/1280 boundary, desktop regression vs baseline, tap)
```

Why preflight M in desktop stage 01: stage 02 decides whether an image field is a single `mediaItem` or a `responsiveMedia` pair, and whether mobile-only text needs a field. Deciding this after the ACF group is saved would force a second `sync`. Preflight writes no scaffold and adds about three figma-cli calls.

`sync <Folder> <desktop-url> <repo> --mobile <mobile-url>` follows the same flow without the stop after 02.

### 4.2 Case B: `mobile <Folder> <mobile-url> <repo>` (OND-7)

```
01m  probe repo, find D:
       D = the export record whose folder == <Folder> and repo == <repo> (newest);
       none found → ask for the desktop URL (figma-cli needs it to rebuild the section map)
     D has no section-map.json → rerun D's scaffold into stage output (no repo write):
       $FIGMA export '<D url>' --dist stages/01-export/output/<D>/scaffold --scaffold next-section
         --component <Folder> --repo-profile .../profile.json --section-map stages/01-export/output/<D>/section-map.json
     $FIGMA export '<M url>' --mobile-of stages/01-export/output/<D>/section-map.json --section-dir <section dir>
       --overlay-out stages/01-export/output/<M> --repo-profile .../profile.json [--class-map ...]
       ── exit 12: CHECKPOINT; exit 11: stop
04m  overlay ── CHECKPOINT only for touch.source=checkpoint rows
05m  verify mobile + desktop regression (the baseline is taken from the repo HEAD before 04m writes)
```

If the map shows content that has no field (figma-cli exit 11: a mobile-only paragraph, a mobile-only image that cannot reuse the desktop field, a mobile crop that needs a `mobile` image), stop. Tell the user the group needs a field, and that the route is `sync <Folder> <desktop-url> <repo> --mobile <mobile-url>`. Never add a field inside the mobile pass.

### 4.3 Interaction with the existing routes

| Route on a paired section | Behavior |
|---|---|
| `resync <Folder> <desktop-url>` | Unchanged. `binding-rules.md` resync already keeps `theme.bps` blocks the user added. Add: "and every rule from a mobile pass (see the pair line in the export record)". Then remind: "mobile pass M may need `resync --mobile`" |
| `resync <Folder> <mobile-url> --mobile` | Mobile pass in drift mode. The new map and overlay are diffed against the existing `bps.mobile` rules only |
| `element <figma-url> <repo> <file> --mobile` | Restyle a control's mobile variant. The edits go only in `bps.mobile` blocks of the target file |
| `status` | Shows D and M as one pair (section 5.2) |

## 5. Run records

### 5.1 Decision: two node folders linked by a pair line

| Option | For | Against |
|---|---|---|
| **A. M gets its own `stages/*/output/<M>/` folders, linked by `pair:` lines (chosen)** | Keeps "a run is keyed by the Figma node id" and the per-node files figma-cli writes. The OND-7 folder `1482-11000` already fits. Re-running mobile does not touch desktop records | `status` must group pairs |
| B. Mobile in `stages/*/output/<D>/mobile/` | One folder per section | Breaks the node-id key. Case B needs D's folder to exist. A desktop rerun "replaces that node's records" and would delete mobile |
| C. A single run key per section folder | Simple status | Large rewrite of every stage's paths. Desktop and mobile records collide |

### 5.2 Record changes (`shared/run-records.md`)

`export-record.md` gains four lines:

```markdown
- viewport: desktop | mobile
- pair: <other node-id> | pending | none | out-of-scope
- baseline (mobile only): <path to the desktop baseline shots> | from-head <git sha>
- section-map: <path> | none
```

- A desktop record written by `new`/`sync` without `--mobile` gets `pair: pending`.
- At the end of desktop 05, the agent asks once: "Mobile design URL, or `mobile out of scope`?" The answer sets `pair:` to the URL's node id (and starts the mobile pass) or to `out-of-scope`.
- `mobile` (Case B) writes `pair: <D>` in M's record and appends `pair: <M>` to D's record when D's record exists. This is the only time a stage edits another node's record, and it adds one line only.
- The desktop scaffold always writes `stages/01-export/output/<D>/section-map.json`, and the record's `section-map:` line points to it. New stage 01m files in `stages/01-export/output/<M>/`: `viewport-map.md`, `viewport-map.json`, `mobile-overlay.json`, `mobile-overlay.styled.txt`, and `nodes.json` (the preflight dump, Case A).
- New stage 05 files: `stages/05-verify/output/<D>/shots/baseline__<W>x<H>.png` (desktop pass), `stages/05-verify/output/<M>/shots/regression__*.png` and `regression-diff.png`.

`status` output for a pair:

```
Section ImageGrid (ora, /home/dev/ora-next/.worktrees/OND-7)
  desktop 3919-20727 (sync)  [01] --> [02] --> [03] --> [04] --> [05]   COMPLETE ...
  mobile  1482-11000 (mobile) [01m] --> [04m] --> [05m]                  COMPLETE ...
```

## 6. Stage changes

### 6.1 Stage 01 export (`stages/01-export/CONTEXT.md`)

- Step 1: also read `--mobile <url>` (Case A) or the `mobile` route (Case B), and record `viewport`. Desktop scaffold step: always pass `--section-map stages/01-export/output/<D>/section-map.json` and record the `section-map:` line.
- New step 3a, mobile preflight (Case A, desktop pass): `$FIGMA inspect '<M url>' > stages/01-export/output/<M>/inspect.txt`, `$FIGMA render '<M url>' --out stages/01-export/output/<M>/figma.png --scale 1` and `$FIGMA export '<M url>' --dump stages/01-export/output/<M>/nodes.json`, plus `$FIGMA export '<D url>' --dump stages/01-export/output/<D>/nodes.json`. No scaffold for M. D's export record gets `pair: <M>`.
- New step 6m (mobile pass, both cases):
  1. If D has no `section-map.json`, first rerun D's scaffold from its record URL. No repo write: `$FIGMA export '<D url>' --dist stages/01-export/output/<D>/scaffold --scaffold next-section --component <Folder> --repo-profile .../profile.json --section-map stages/01-export/output/<D>/section-map.json [--font-map ...]`.
  2. Run `$FIGMA export '<M url>' --mobile-of stages/01-export/output/<D>/section-map.json --section-dir <app root>/<sectionsDir>/<Folder> --overlay-out stages/01-export/output/<M> --repo-profile .../profile.json [--class-map stages/04-conform-bind/output/<D>/class-map.json] [--font-map ...]`, with the same `--font-map` as D's record.
  3. Exit 0: continue. Exit 12 (`unmatched` or `target-missing` rows): **checkpoint** on `viewport-map.md`. The user fixes rows there (edit surface), the agent carries the edits into `viewport-map.json`, then reruns step 2 with `--map <edited viewport-map.json>`. Exit 11 (`new-content` rows): stop with the `sync --mobile` message (section 4.2).
- Step 9 routing: on `viewport: mobile`, load `../04-conform-bind/CONTEXT.md` in mobile mode. Audit additions: the record has `viewport`, `pair` and `section-map`, and the map has no `unmatched` or `target-missing` row left without a user decision.
- New reference `stages/01-export/references/viewport-map.md` (under 80 lines): how to read and edit the figma-cli output, the columns, the match rules (6.1.1), the statuses and the affordance guess.

#### 6.1.1 Viewport map: columns and match rules (implemented in figma-cli, F2)

| Column | Meaning |
|---|---|
| `mobile node` | Name and id in M |
| `desktop target` | Class in the section (`.grid-card.slot-tall-end`) or node in D |
| `status` | `same` (restyle only), `moved` (order changes), `hidden-on-mobile`, `mobile-only-decor` (icon, divider: no field), `new-content` (needs a field: stop), `unmatched`, `target-missing` (a scaffold class that stage 04 renamed or removed in the repo) |
| `order` | Visual index in M, and in D |
| `box` | Mobile width × height and sizing (fixed, hug, fill) |
| `deltas` | Font size, line height, letter spacing, padding, gap, radius, fill, shadow, direction, compared with D |
| `interaction` | D hover variant, the M affordance, and the touch source (`design` or `checkpoint`) |

Match signals, strongest first. All of them come from the scene and the section map, because `inspect.txt` does not print text characters:

1. TEXT nodes with equal normalized `characters` (trimmed, whitespace collapsed, Hebrew niqqud stripped). OND-7 matched cards by title this way.
2. Image fills with the same `imageRef`. The same WordPress image is usually placed in both frames.
3. Instances of the same `componentId` or component set (card variants `Property 1=Default` and `Variant2`).
4. Same layer name and the same order among siblings. Weak, because Figma names like `Frame 1562162393` repeat.

When no signal matches, the row is `unmatched` and goes to the checkpoint. The matcher never guesses.

### 6.2 Stage 02 field plan (Case A only)

- Inputs add `stages/01-export/output/<M>/inspect.txt` and `figma.png`, when the desktop record has `pair:`.
- Rule additions in `field-plan-rules.md`:
  - When the mobile frame shows an image in a different aspect ratio or crop, plan it as a `responsiveMedia` pair (desktop + mobile) and say so in the "why" column. Otherwise a single `mediaItem`, which `ResponsiveImage` uses for both viewports.
  - Text that appears only on mobile is a field only if an editor changes it. Decorative chevrons and arrows are never fields.
  - Questions list: "mobile shows X that desktop lacks" goes to the user.

### 6.3 Stage 03 fragment

No change. A mobile pass never writes the `.gql`.

### 6.4 Stage 04 conform-bind (`binding-rules.md`, new section "mobile: overlay")

Inputs add `mobile-overlay.json` and `mobile-overlay.styled.txt` from `stages/01-export/output/<M>/`, the user-edited `viewport-map.md`/`.json`, and `skills/next-section-repo/references/mobile-patterns.md`.

Rules:

1. **Desktop is frozen.** Do not change any declaration outside a `theme.bps.mobile` block, except to gate an existing `:hover` rule (rule 5). The audit checks this against the git diff and the 1440 regression shot.
2. **Overlay, not scaffold.** For each overlay selector, nest its `bps.mobile` block (from `mobile-overlay.styled.txt`) in the selector of the map's `desktop target`. Never copy a mobile scaffold's structure or class names.
3. **Order without new markup.** When `moved` rows change visual order, use CSS first (`order`, `grid-template-areas`, `display: contents` on wrapper rows). Change JSX only when CSS cannot express the order, and say why. Keep the page direction rules from `section-shape.md`: the root stays `ltr`, and a mobile grid that must read right to left sets `direction: rtl` on that grid.
4. **Hidden and decor.** `hidden-on-mobile` → `display: none` in `bps.mobile`. `mobile-only-decor` → search the repo's icons first (2.6), then add the element and hide it outside mobile.
5. **Touch path from the design.** Apply rows with `touch.source=design` as the frame shows: a tap toggle (`useState` + `.is-open`) on the recorded trigger, and the existing hover gated with the repo's gate (2.5). Checkpoint only rows with `touch.source=checkpoint`: tap toggle, always shown on mobile, or hidden. Apply only the chosen option. This is the step 5 checkpoint, together with the drift list per map row and the icon decision.
6. **JS only when the markup differs.** Use `useIsMobile` (the import from the profile, T10) only for content swaps (2.3), never for layout.
7. **Specificity.** Nested blocks first. Use a trailing root-level block only when slot selectors require it, and record why.
8. **No fields.** A `new-content` row should already have stopped the run in 01m. If one shows up here, stop the same way.
Audit additions (mobile mode):

| Check | Pass condition |
|---|---|
| Desktop frozen | `git diff` shows no removed or changed desktop declaration outside `bps.mobile`, except the recorded hover gates |
| Nesting | Every mobile rule is nested, or the record gives the reason for a trailing block |
| Touch | Every hover reveal has its touch path from the design, or a recorded checkpoint decision |
| Icons | Every new icon has the list of repo candidates that were rejected |
| Untouched | `.gql` and `Server<Folder>.js` unchanged |

`conform-record.md` (mobile) holds: the pair, the map rows applied, the touch paths (design or decided), the icon decisions, the specificity notes and the `check_section.py` summary.

### 6.5 Stage 05 verify (`verify-steps.md`, new "Mobile" section)

| Check | How | Pass |
|---|---|---|
| Level 1 mobile | `screenshot.js` of M's `preview.html` at M's PNG size, `diff.js` against M's `figma.png` (both in `stages/01-export/output/<M>/`) | `diffRatio` recorded, comparable between runs |
| Fluid mobile | `measure.js` on M's fluid preview at `320x700,375x812,<M width>x900,768x1024,1279x800` | no overflow |
| Level 2 or harness | App route, or the harness (T12) when the app cannot start, at the same widths | no overflow, and `--selector` finds the section |
| Boundary | Screenshots at 1279 and 1280. In ora `bps.desktop` and `bps.mobile` both apply at 1279 (`min-width: 1279px` and `max-width: 1279px`) | 1279 shows mobile, 1280 shows desktop, with no mixed state. A mixed state is listed |
| Desktop regression | Diff the 1440 shot after 04m (`stages/05-verify/output/<M>/shots/`) against the baseline (Case A: `stages/05-verify/output/<D>/shots/baseline__<W>x<H>.png`; Case B: taken from HEAD before 04m) | diff ratio ≤ 0.001 for the section element, or each difference listed |
| Touch | `interact.js` at 393 (or M's width): tap the recorded trigger of each reveal card, screenshot, tap again | matches the recorded touch path |
| Look | Order, sizes and decor against M's `figma.png` | same, or each difference listed |

The 1920/1440/1100 desktop checks stay as they are for the desktop pass.

### 6.6 `CLAUDE.md` and `CONTEXT.md`

- Triggers table:

| Keyword | Action |
|---|---|
| `new <figma-url> <repo> [--mobile <url>]` | New section. 01, 02, stop. With `--mobile`, the mobile pass follows 05 |
| `sync <Folder> <figma-url> <repo> [--mobile <url>]` | Unchanged, plus the mobile pass after 05 |
| `mobile <Folder> <mobile-url> <repo>` | Mobile design for a section whose desktop is built: 01m, 04m, 05m |
| `resync … [--mobile]` | `--mobile` resyncs the mobile pass only |

- Ground rule: "Never derive a mobile design from a desktop frame or the reverse. A mobile pass needs the mobile URL from the user."
- `CLAUDE.md` is already 79 lines and the limit is 80. Move "How `status` works" (about 10 lines) into `shared/run-records.md` and point to it.
- Update the "What to Load" table: 01m loads `viewport-map.md` and the repo skill's `mobile-patterns.md`. 04m loads `mobile-patterns.md`, not the stage 02/03 references.
- `CONTEXT.md` routing: one row "Add the mobile design" → `stages/01-export/CONTEXT.md` (mobile route).

### 6.7 next-section-repo skill

- New `references/mobile-patterns.md` (section 2 condensed, under 120 lines, touch rule design-driven first with the checkpoint as fallback). It is the canonical home for mobile rules, and `section-shape.md` "Styles" links to it instead of repeating them.
- `conformance-checklist.md`: replace the `bps-present` (warn) row and the "touch fallback" manual row with a "Mobile" group. It points to `mobile-patterns.md` and lists the new check ids (T10).

### 6.8 Setup questionnaire

No new questions. Mobile widths come from the M frame and the profile. A `mobile` test route is the same test route.

## 7. Tooling

### T10 `probe_repo.py`: additive profile keys (schemaVersion stays 1)

| Key | Value |
|---|---|
| `theme.breakpoints` | Numbers from the `breakPoints` object the theme uses (ora `{mobile: 1279, smallerMobile: 320, laptop: 900}`) |
| `theme.bpsMedia` | Each `bps` key → its media string after substitution |
| `theme.mixins` | The mixin keys present on the ThemeProvider theme (ora: no `shrink`, no `layout`) |
| `theme.layoutHeights` | The layout height keys present on the ThemeProvider theme (ora: no `mobileHeader`) |
| `mobile.hook` | `{import, count}` per `useIsMobile` import source, most used first |
| `mobile.responsiveImage` | Path of the `ResponsiveImage` component, or null |
| `mobile.hoverGate` | `"hover-media"` when `@media (hover: hover)` is used in sections, `"bps-desktop"` when hover sits inside `bps.desktop`, otherwise null |
| `mobile.icons` | `public/icons` path and the inline icon component folders found |

Warning: "`bps.desktop` and `bps.mobile` both match at <N>px" when the ranges overlap (ora today).

`repo-profile.md` documents the keys. Tests in `test_next_section_repo.py` use a fixture theme with an overlap and one without.

### figma-cli changes (`/home/dev/cli/figma-cli`)

**F1. Desktop section map.** New flag `--section-map <file>` on `export … --scaffold next-section`. While `renderScaffold` (`src/react.ts` L245) builds the scaffold, it records one row per node that got a class (`roleClassName` L155). Schema v1 is fixed up front so agents can work in parallel:

```json
{ "schemaVersion": 1, "viewport": "desktop", "node": "3919-20727", "component": "ImageGrid", "rows": [{
  "nodeId": "", "className": "", "selector": ".grid-card .card-title", "role": "title", "parentId": "", "order": 0,
  "text": "normalized", "imageRefs": [], "componentId": null, "componentSetId": null, "box": { "w": 0, "h": 0,
  "sizing": "fixed|hug|fill" }, "decls": { "font-size": "32px" }, "hover": { "reveals": true, "decls": {} } }] }
```

**F2. Matcher (pure module `src/viewport-map.ts`).** Input: the M scene (`parseScene` + `loadStates` + `readComponentSets`) and the D section map. It applies the 6.1.1 signals in order and assigns the 6.1.1 statuses. A row is `target-missing` when its class does not occur in the repo's `Styled<F>.js`/`Client<F>.js`, read as text through `--section-dir`. Desktop stage 04 often renames scaffold classes (OND-7: scaffold `card-2`…`card-6` became `grid-card ${slot}`), so targets resolve in this order: `--class-map <json>` (scaffold class to repo selector, written by desktop 04 as `stages/04-conform-bind/output/<D>/class-map.json`, or filled once at the 01m checkpoint for older sections), then the class itself, then the class with its `-<n>` suffix stripped. Small vector or image nodes inside a matched card with no desktop counterpart become `mobile-only-decor`, with an `affordance: chevron|arrow|plus` guess.

**F3. Mobile mode and overlay emitter (`src/mobile-overlay.ts`, wired in `src/cli.ts`, `src/scene.ts`, `src/export.ts`).** Command: `$FIGMA export '<M url>' --mobile-of <D section-map.json> --section-dir <dir> --overlay-out <dir> --repo-profile <profile.json> [--font-map …] [--map <edited viewport-map.json>]`.

- Computes M's declarations with the existing `layout-css.ts` helpers and `themeTokens` (`react.ts` L367) and diffs them against each row's `decls`. Text and spacing use px from the frame. Containers stay fluid.
- Outputs: `viewport-map.json`, `viewport-map.md` (the edit surface), `mobile-overlay.json` (per selector: decls, hide, order hints, decor, touch) and `mobile-overlay.styled.txt` (ready-to-nest `${({ theme }) => theme.bps?.mobile} { … }` blocks using the profile's bps key). With `--map`, the user's edits win over the matcher. It never writes into the repo.
- Touch object: when the D row has `hover.reveals` and the matched M node has a prototype tap (an `ON_CLICK` change-to, as OND-7's `H01 1565:4763` and `H02 1565:4839` have, pointing at the expanded `Variant2`) or an affordance inside it, `touch: { source: "design", trigger: <node carrying the reaction>, mirror: ".is-open" }` plus the hover gate from the profile's `mobile.hoverGate` (default `bps.desktop`). With no affordance, `touch: { source: "checkpoint" }`.
- Exit codes: 0 ok; 12 files written but `unmatched` or `target-missing` rows exist (checkpoint); 11 `new-content` rows exist (stop). Exit 5 is taken by `rate-limited`, so the checkpoint is 12.

**F4. Tests and ship.** Add `test/section-map.test.ts`, `test/viewport-map.test.ts` and `test/mobile-overlay.test.ts` (node:test with inline wire, like `scaffold.test.ts`) to the explicit list in `package.json` `scripts.test`. Fixtures: `test/fixtures/ond7-desktop.json` and `test/fixtures/ond7-mobile.json`, recorded sessions of `3919-20727` and `1482-11000` (every nodes response, including hover and tap states; dumps carry `imageRef` only, no URLs) captured with `scripts/capture-fixture.ts` and replayed offline through an injectable client (`test/replay-client.ts`). Expected: 6 cards matched by title, the intro matched, 6 chevrons as decor with affordance, the breadcrumbs `same`, and 6 `touch.source=design`. Against the OND-7 section files, exit 12 without a class map (the renamed cards are `target-missing`) and exit 0 with it. Ship: `npm run ci`, commit in figma-cli, `npm run ship:workspace`, commit the binary in the workspace (`shared/figma-cli-setup.md`). Update `shared/export-contract.md` with `--dump`, `--section-map`, the mobile mode and exits 11 and 12.

### T12 Section harness (promoted from the OND-7 `css-check/`)

- `skills/next-section-repo/scripts/harness.py --repo <app root> --folder <F> --out-dir <dir> [--props <json>]`.
- Bundles `Client<F>.js` with esbuild from a checkout that has `node_modules` (the worktree's own, else the main checkout's, found through `git worktree list`). Stubs `MediaBackground`, `Breadcrumbs` and `next/font/local`. Imports the repo's real theme module (instead of OND-7's hand-written theme), so `bps` strings are exact.
- Writes `index.html` and `bundle.js` only under `--out-dir` (the stage output), never in the repo.
- Stage 05 uses it when Level 2 cannot start, and always for the desktop regression and tap checks, because it is deterministic.
- The record states that media and breadcrumbs are stubbed, so it never claims to be Level 2.

### `check_section.py` new checks (part of T10)

| Id | Status | Rule |
|---|---|---|
| `bps-overlap` | warn | The profile has the overlap warning and the section uses `bps.desktop` |
| `mobile-nested` | warn | Root-level `bps.mobile` blocks with more than N descendant selectors |
| `hover-gated` | fail after a mobile pass, otherwise warn | A `:hover` rule that reveals content (opacity, grid rows, display) outside the repo's hover gate |
| `no-hardcoded-bp` | fail | A literal `@media (max-width: 1279px)` or similar instead of `theme.bps` |

## 8. Tasks

Phase 1 is workspace docs. Phase 2 adds tools (figma-cli F1-F4, T10, T12). Phase 3 is acceptance.

| Task | Phase | Files | Depends on | Size |
|---|---|---|---|---|
| T1 Triggers, ground rule, status moved out | 1 | `CLAUDE.md`, `CONTEXT.md` | none | S |
| T2 Pair records and status format | 1 | `shared/run-records.md` | T1 | S |
| T3 Mobile route, preflight, section map and step 6m in stage 01 | 1 | `stages/01-export/CONTEXT.md` | T2 | M |
| T4 Viewport map reference (reading and editing the F2 output) | 1 | `stages/01-export/references/viewport-map.md` | T3 | S |
| T5 Responsive field rules | 1 | `stages/02-field-plan/CONTEXT.md`, `references/field-plan-rules.md` | T3 | S |
| T6 Mobile pattern reference | 1 | `skills/next-section-repo/references/mobile-patterns.md`, `section-shape.md` | none | M |
| T7 Mobile overlay rules, checkpoint and audit | 1 | `stages/04-conform-bind/CONTEXT.md`, `references/binding-rules.md` | T4, T6 | M |
| T8 Mobile verify | 1 | `stages/05-verify/CONTEXT.md`, `references/verify-steps.md` | T7 | M |
| T9 Checklist Mobile group | 1 | `conformance-checklist.md` | T6 | S |
| T10 Probe keys and checker checks, with tests | 2 | `probe_repo.py`, `check_section.py`, `repo-profile.md`, tests | T6 | M |
| F1 `--section-map` sidecar, with test | 2 | `/home/dev/cli/figma-cli`: `src/react.ts`, `test/section-map.test.ts` | fixtures | M |
| F2 Matcher, with test | 2 | `/home/dev/cli/figma-cli`: `src/viewport-map.ts`, `test/viewport-map.test.ts` | fixtures, F1 schema | L |
| F3 Mobile mode and overlay emitter, with test | 2 | `/home/dev/cli/figma-cli`: `src/mobile-overlay.ts`, `src/cli.ts`, `src/scene.ts`, `src/export.ts`, `test/mobile-overlay.test.ts`, `package.json` | F1, F2 | L |
| F4 CI, ship and export contract | 2 | `/home/dev/cli/figma-cli`, workspace binary, `shared/export-contract.md` | F3 | S |
| T12 Harness | 2 | `skills/next-section-repo/scripts/harness.py` (+ `.mjs`) | T8 | M |
| T13 Replay OND-7 (Case B) | 3 | none in the repo, a fresh worktree | T1–T10, T12, F1–F4 | M |
| T14 Dry run of Case A on a new section | 3 | none | T13 | M |

Conventions to keep while editing: every `CONTEXT.md` under 80 lines, every reference under 200, one canonical home per rule (mobile rules live only in `mobile-patterns.md` and `binding-rules.md` "mobile: overlay"), one-way references (stage files point to the skill, never the reverse), and no stage outputs committed.

### Execution with parallel agents

The F1 schema and the F3 outputs are fixed up front, so tasks can run in waves. Rule: each agent owns its files, and no two agents in a wave edit the same file. figma-cli agents work in separate worktrees, and the orchestrator merges them.

| Wave | Runs | Agents |
|---|---|---|
| 0 | one agent, network | Fixtures: dump `3919-20727` and `1482-11000` into `test/fixtures/` (image URLs stripped) |
| 1 | parallel | F1; F2; T1+T2; T6+T9; T10 |
| 2 | parallel | F3; T3+T4+T5; T7+T8; T12 |
| 3 | F4, then parallel reviews | F4 ship and export contract; then a bugbot review of the figma-cli diff, a workspace conventions audit (line limits, one canonical home, one-way references), and a check that the doc flags match `$FIGMA help` |
| 4 | sequential | T13, then T14, in a fresh OND-7 worktree. Nothing is pushed |

## 9. Acceptance

**T13, OND-7 replay (Case B).**

1. Create a worktree from `5242142` (the desktop-only state, before `8ccedaa`). Run `mobile ImageGrid '<1482-11000 url>' <that worktree>`.
2. Pass conditions:
   - The map comes from figma-cli exit 0 after the class-map checkpoint (exit 12 on the first run is expected: OND-7 renamed the card classes). It matches all 6 cards and the intro with no manual fixes, and lists the chevrons as decor.
   - No touch question is asked: the run applies the chevron tap toggle from the design, with the hover gated by `bps.desktop`.
   - The icon search runs before any SVG is drawn.
   - `git diff 5242142` shows changes only inside `bps.mobile` blocks plus the hover gates.
   - The 1440 regression diff is ≤ 0.001.
   - The 1279/1280 boundary check reports the ora overlap.
   - The result matches `8ccedaa` visually at 393. Code differences, such as nested vs trailing blocks, are listed, not failed.
3. The worktree is removed after the replay. Nothing is pushed.

**T14, Case A dry run.** On a section with both frames, run `new <desktop> <repo> --mobile <mobile>`. Check that:

- stage 02 lists the image fields as responsive pairs where the crops differ;
- the run stops after 02;
- `continue` carries on through desktop 05, then mobile 01m–05m, with no new trigger;
- `status` shows the pair.

## 10. Risks and open questions

| Item | Note |
|---|---|
| ora 1279 overlap | Fixing `theme/index.js` (desktop `min-width: 1280px`) is a repo change outside this workspace. The plan only reports it. Should a separate ora task fix it? |
| ora `mixins.shrink`/`mobileHeader` wiring | ora's ThemeProvider theme lacks them (2.2). Wiring them in is a separate ora task, not part of this plan |
| Tap target | Resolved by the design: the toggle goes on the node that carries the prototype `ON_CLICK` (on OND-7 the card instance, with the chevron as the affordance). When the frame has an affordance and no reaction, the trigger is the affordance's nearest matched card |
| `field-report.md` on pair runs | The workspace keeps it beside the component and not ignored, and on OND-7 you purged it from history [35bc612e]. Should it move to stage output instead? That would be a separate change |
| Map quality on generic text | Repeated labels ("לפרטים נוספים") match several nodes. The matcher marks them `unmatched` when it cannot tell them apart by order |
| Harness scope | Stubbed media cannot show `ResponsiveImage` choosing the mobile image. That check needs Level 2 |
