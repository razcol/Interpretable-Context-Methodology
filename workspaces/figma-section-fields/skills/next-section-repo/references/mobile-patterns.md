# Mobile patterns

How a section handles mobile in any of the five section repos (ora, smart, jaecoo, luxury-trade, omoda). App roots: `/home/dev/ora-next/code/app`, `/home/dev/smart-next/code/app`, `/home/dev/jaecoo-next/code/app`, `/home/dev/colmobil-luxury-trade/code/app`, `/home/dev/omoda-next/code/app`. This file holds the rules. Per-repo values (breakpoint queries, theme mixins, layout heights, hover gate) live in the repo profile, defined in [repo-profile.md](repo-profile.md). Bracketed ids like `[657777ae]` are chat transcript ids, not commits.

## Breakpoints

- Use only `theme.bps` keys (`profile.theme.bps`), always written as:

```js
${({ theme }) => theme.bps?.mobile} {
  ...
}
```

- Never hard-code `1279px`, `1280px` or any other width in an `@media` query.
- There is one real breakpoint, 1279/1280. "Mobile" covers phones and tablets. No repo has a `tablet` key.
- CSS is desktop-first. Base rules are desktop. Mobile is the override.
- Exception: ora's `bps.desktop` is `min-width: 1279px`, so at exactly 1279px both `bps.mobile` and `bps.desktop` match. The profile reports this as an overlap warning. A section that uses `bps.desktop` in ora must be checked at both 1279 and 1280.

## Where mobile rules go

Nest each `bps.mobile` block inside the selector it overrides:

```js
.card-title {
  font-size: 32px;

  ${({ theme }) => theme.bps?.mobile} {
    font-size: 24px;
  }
}
```

A single trailing block at the root is allowed only when nesting cannot win on specificity, for example slot rules like `.grid-card.slot-*` that need the same weight. Record the reason in the run record.

## Values

- Plain `px` taken from the mobile frame. `vw` only when the frame is clearly fluid.
- No new `!important`. Add one only when a nested component wins otherwise, and record why.
- The side gutter comes from the mobile frame, never from another section or a note.
- Theme mixins and layout heights differ by repo. ora's ThemeProvider theme has no `mixins.shrink`, `mixins.layout` or `layoutHeights.mobileHeader`. Read the profile keys `theme.mixins` and `theme.layoutHeights` before using any of them. Where `layoutHeights.mobileHeader` (or `mobileNavbar`) is present, use it for offsets such as `scroll-margin-top`.

## `useIsMobile`

- ora has a local `hooks/useIsMobile` (`react-use` `createBreakpoint` plus `useEffect`, returns `breakpoint === 'mobile'`) and the shared `@colmobil/next/core/hooks/useIsMobile`. The other repos use only the shared hook.
- Both return `false` on the server and on first paint, so desktop markup renders first.
- Use CSS for layout, order, size and visibility. Use the hook only when the markup or the content differs: another component, truncated text, a mobile-only button list, or choosing a mobile media source.
- In a new section, import the hook the repo uses most. In ora that is the shared hook, which `ResponsiveImage` also uses.

## Media

- When the mobile frame crops or composes an image differently from desktop, the field is a desktop/mobile pair: the `responsiveMedia` role in `profile.fragments` (`imageFields { desktop { ... } mobile { ... } }`). Decide this in the field plan, before the ACF group exists.
- `@/Core/Image/ResponsiveImage` picks `mobile` when `isMobile` is true and the mobile image exists, and otherwise falls back to `desktop`. `MediaBackground` passes `imageFields` through to it.
- Backgrounds set from props pick `isMobile ? mobile?.node?.src || desktop?.node?.src : desktop?.node?.src`. Video uses `videoFields.{desktop,mobile}` the same way.

## Hover and touch

The touch path is a product requirement read from the mobile frame, not an agent choice.

When desktop reveals content on hover, look at the same element in the mobile frame:

1. It has a tap reaction (an `ON_CLICK` change-to an expanded variant) or a disclosure affordance (chevron, arrow, plus). Implement a tap toggle as the frame shows it:
   - `useState` in the client component, and `.is-open` on the element that carries the reaction.
   - Inside `bps.mobile`, mirror the desktop reveal under `.is-open`.
   - Gate the existing `:hover` with the repo's gate, from the profile's `mobile.hoverGate`: `hover-media` means `@media (hover: hover)`, anything else means `bps.desktop`.
   - On OND-7 `ImageGrid` the whole card carries the `ON_CLICK` and the `onClick`. The chevron is the visible affordance and rotates when open.
2. The frame shows neither. Stop at a checkpoint and ask: tap toggle, always shown, or hidden.

`cursor: pointer` only where there is a link or a handler.

## Hiding and showing

- Default: `display: none` inside a `bps.mobile` (or `bps.desktop`) block.
- JS (`{isMobile && ...}`) only when the hidden element is heavy or has different content.

## Icons

Search the repo before drawing one: `public/icons/*.svg` (used through `Image` or `ResponsiveImage`) and inline icon components (for example ora `Layout/ContactUs/Assets/Icons/ClockIcon.js`). Present the candidates. Draw a new inline SVG only after the user says none fits [657777ae].

## Overlay from figma-cli

On the mobile pass, `figma-cli export --mobile-of` writes `mobile-overlay.styled.txt`: `bps.mobile` blocks keyed by the desktop selectors. They are values to nest into the existing selectors of `Styled<F>.js`, following the rules above. Never copy them as a structure, and never change desktop rules to fit them.

With `--section-dir`, the tap reveals under `&.is-open` copy the section's own `:hover` rules, so nest them as they are and add only the state and handler. Background and shade blocks set paint on existing elements (for example `.card-shade`); photos still come from WordPress.
