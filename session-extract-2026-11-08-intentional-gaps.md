# Intentional gaps from the desktop-then-mobile session

## Request and markers

Extract, from session `70677439-c101-468e-b747-2f1c044c6b9d`, items the agent left unimplemented on purpose that it still said could or should be done, with the reason given for leaving them. Markers were derived: the session uuid, `intentionally`, `not implemented`, `deferred`, and `out of scope`. The scan was limited to project slug `home-dev-ai-system` because the user named one session in this workspace.

## Coverage

- Projects root: `/home/dev/.cursor/projects`. Slug count in this scan: 1 (`home-dev-ai-system`). Other slugs were not scanned.
- Parent transcripts scanned: 48. Files matched: 7. Files discarded as incidental: 6. Example: `0bbc94f8-ee60-4f29-b478-bbcd1fe20a47` matched `intentionally` in a question about whether Rovo suggestions were reasonable, not in a deferral list.
- Subagent files opened: `2ea82aad-7485-4f01-82e9-aec9022c25eb` (T13, the replay the parent cites for the open overlay list), plus `d1f757a8-9f20-4feb-bfea-cdf3b9418f8d` (F3, the overlay emitter) and `50ac382a-852d-4527-b8c9-0ac71bc1ad3f` (viewport matching). The parent is the build of this feature, and the deferred list is only explained in T13.
- Orphan session folders: 0.
- Stores not read: `state.vscdb`, `~/.cursor/chats/*/store.db`, agent-store sqlite. `conversation-search.db` was not the search.

## Sessions

- `70677439-c101-468e-b747-2f1c044c6b9d` — home-dev-ai-system — 2026-11-05 — core — built the desktop-then-mobile plan for figma-section-fields and figma-cli, then left the overlay value bugs as a later figma-cli change — "Plan v2: desktop first, then mobile" — `/home/dev/.cursor/projects/home-dev-ai-system/agent-transcripts/70677439-c101-468e-b747-2f1c044c6b9d/70677439-c101-468e-b747-2f1c044c6b9d.jsonl`
- `2ea82aad-7485-4f01-82e9-aec9022c25eb` — home-dev-ai-system — subagent of the parent — partial — T13 replay that recorded each overlay adaptation it had to do by hand — cited from the parent as [T13 OND-7 mobile replay](2ea82aad-7485-4f01-82e9-aec9022c25eb)

## Keep

- `70677439-c101-468e-b747-2f1c044c6b9d`: class-map rerun fixes shipped (`8896b3f`, then `6098676`). An unchanged first-run row, including a fallback target, no longer counts as a user edit. 176 tests and the build passed on the second fix.
- `70677439-c101-468e-b747-2f1c044c6b9d`: workspace doc fixes through `04a23fa` (load lists, worktree record matching, scaffold rerun path, chevron `display: none` exception, pre-existing checker failures, verify harness paths).

## Extra or harmful

- `2ea82aad-7485-4f01-82e9-aec9022c25eb`: T13 had to hand-edit overlay output because the emitter's values were wrong for the OND-7 section. The parent did not treat those hand edits as a fix of figma-cli.

## Still missing

Still open, from the parent's closing note in `70677439-c101-468e-b747-2f1c044c6b9d`. One shared reason: after T13, the agent judged a full overlay-quality fix "too much scope" while docs were still being corrected, and these items "change what the overlay generates," so they were split into a separate figma-cli follow-up. T13 still passed because each adaptation was written in the conform record. The close says they "need a separate figma-cli change if you want it."

1. **Font weight on the row.** `.row-top` gets `font-weight: 900`, which would also hit the intro. T13 skipped it because the intro needs weight 400. Still open.
2. **Row height vs the shorter card.** `.row-bottom` gets `height: 245px`, but that repo row also holds the 160px-wide card. Still open.
3. **Caption alignment from a left-to-right frame.** Values such as `flex-end` come from an LTR frame; the cards are RTL, so the meaning flips. Still open.
4. **Reveal selectors.** Tap-reveal rules still name the scaffold (`.card-media::before`, `.card-caption::before`) rather than the repo classes. Still open in the parent's close. F3 (`d1f757a8-9f20-4feb-bfea-cdf3b9418f8d`) had already tried a class-map translation; T13 still had to adapt these on the real section.
5. **Background and shade fills.** Not emitted. T13's comparison with `8ccedaa` called out the missing `#fbfbfb` background, mobile card shadow, and per-card shade strengths. Still open.

T13 also recorded two adaptations in the same bullet that the parent's closing five do not repeat. Same deferral, still not called fixed:

6. **`order` hints** mix two parent levels, so T13 ignored them and used grid areas. Still open as an emitter issue.
7. **Intro height.** The overlay does not reset the intro's fixed 616px height. Still open as an emitter issue.

## Out of scope

The parent also listed items it refused to treat as work. These were left unchanged because the agent said they were not product gaps:

- **Check d / `field-report.md`:** the test brief forbade writing into the repo; the docs deliberately put `field-report.md` beside the component (`70677439-c101-468e-b747-2f1c044c6b9d`).
- **Missing mobile profile:** T14 hit it because the brief ran the mobile export early. Normal order creates that profile first.
- **Section path:** the path given to T14 does not exist in the main checkout; the parent called that its own brief mistake.
- **Hover-image question:** the parent said it does not apply to this section.

## Implications

No skill or workspace edit is required for the extract itself. If the overlay follow-up is picked up, it belongs in figma-cli's mobile overlay emitter (`src/mobile-overlay.ts` and the viewport target resolver), not in the stage docs. The five closing items, plus the two T13-only items above, are the change list. Recommendations only; this report does not edit that tool.

## Gaps

- Other `~/.cursor/projects` slugs were not scanned.
- Tool results inside the jsonl are often missing; the overlay list is taken from later assistant text in the parent and from T13's final report.
- No claim is made about sessions on another machine or in the Windows Cursor profile.
- Whether items 4, 6, and 7 are already fixed in the current figma-cli tree was not re-checked against the product files. The parent, at the end of this session, still called the overlay list open.
