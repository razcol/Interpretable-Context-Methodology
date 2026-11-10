# Overlay follow-up: what the clarification sessions left to implement

## Request and markers

Read session `c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b` and its side chat `164e2694-60a4-4632-b5f7-a70600921381`, and list the implementations that still need to be done for the figma-section-fields desktop-then-mobile path to be complete. Markers passed to `scan_transcripts.py` (derived by the agent, project `home-dev-ai-system`): the two session uuids, `mobile-overlay\.ts`, and `font-weight: 900`.

## Coverage

- Projects root `/home/dev/.cursor/projects`, 1 slug scanned (`home-dev-ai-system`).
- 49 parent transcripts scanned, 3 matched, 1 discarded as incidental: `0636017a-c976-4b80-971f-8a39dab0d0ed` (3 Nov) matched only `font-weight: 900` in desktop scaffold work, before the mobile overlay existed.
- `164e2694-60a4-4632-b5f7-a70600921381` is not a parent; it is a subagent file of `c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b` (the side chat that inherited the parent's history). It was opened because the user named it. `2ea82aad-7485-4f01-82e9-aec9022c25eb` (the T13 replay, a subagent of `70677439-c101-468e-b747-2f1c044c6b9d`) was reopened for the exact overlay list, because both named sessions only restate it.
- Orphan folders: 1, `ab098419-6d73-4890-a1a3-e944a54cad2e`, which is the current session.
- Stores not read: `state.vscdb`, `~/.cursor/chats/*/store.db`, agent-store sqlite; `conversation-search.db` was not the search.

## Sessions

- `c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b` — home-dev-ai-system — 2026-11-08 — core — extracted the intentionally deferred items from the build session, then explained them in plain terms — "So the agent essentially telling me- fix if you want this to actually work fully" — `/home/dev/.cursor/projects/home-dev-ai-system/agent-transcripts/c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b/c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b.jsonl`
- `164e2694-60a4-4632-b5f7-a70600921381` — home-dev-ai-system — 2026-11-08 — core — side chat on what "address these / skip them" means — "what do you mean by that?" — `.../c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b/subagents/164e2694-60a4-4632-b5f7-a70600921381.jsonl`
- `70677439-c101-468e-b747-2f1c044c6b9d` — home-dev-ai-system — 2026-11-05 — partial — the build session the two above analyse; its T13 subagent `2ea82aad-7485-4f01-82e9-aec9022c25eb` holds the source list.

## Keep

- `c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b`: the split into two piles is right. Only the overlay emitter list is product work. Field report placement, the missing mobile profile, the section path and the hover image were test-brief noise and stay as they are.
- `c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b`: the finished OND-7 section (`8ccedaa`) is correct and is not part of the backlog. The fixture `test/fixtures/ond7-section/StyledImageGrid.js` in figma-cli is that hand-finished version.

## Extra or harmful

- `c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b`: the examples ("bold intro") read as OND-7-specific. The user had to ask whether a fix would mean "intros are never bold". The answer given was correct (the bug is a parent-level declaration leaking to a child, not intros), but each item should be stated as a general rule.

## Still missing

All seven items were still open at figma-cli `6098676` on branch `mobile-overlay`, the state these sessions describe. They were reproduced offline from the OND-7 fixtures before any change (`c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b`, `2ea82aad-7485-4f01-82e9-aec9022c25eb`). Each is stated here as the general rule it breaks:

1. **Inherited text properties leak.** A text style declared on a mobile container (`.row-top { font-weight: 900 }`) is emitted on the repo container, which holds different children (the intro). The emitter compares declared values, not inherited ones, and also lists false resets on the cards.
2. **Container size when the children differ.** `.row-bottom { height: 245px }` comes from a mobile row that holds only the square cards. The repo row also holds the 160px wide card.
3. **Alignment from a left-to-right frame.** `flex-start`/`flex-end` values come from LTR Figma frames, but they are applied to `direction: rtl` repo elements.
4. **Reveal selectors name scaffold structure.** `.card-media::before`, `.card-caption::before` and `.card-caption .card-text` are used instead of the repo's `&::before` and `.card-text`.
5. **Fills are dropped.** The compared properties do not include `background` or `box-shadow`, so the root `#fbfbfb`, the mobile card shadow and the per-card shade gradients are never emitted.
6. **`order` across parent levels.** Elements that moved to another parent on mobile get `order` values relative to the wrong siblings.
7. **Size resets are comments only.** `rowDeltas` drops a height delta when the mobile box hugs its content, so the desktop intro's `height: 616px` is never reset. Resets in general appear only as `# resets:` comments.

## Out of scope

- The workspace doc problems T13 listed (load lists, record matching, the harness `--repo` path, binding-rules 1 vs 4) were fixed in `70677439-c101-468e-b747-2f1c044c6b9d` through `04a23fa`, or fall outside the user's question.
- Inventing a new layout (`display: contents` plus `grid-template-areas`, as `8ccedaa` did). The emitter should report reparenting clearly, not design the grid.

## Implications

- figma-cli: fix the items in `src/mobile-overlay.ts`, plus the compared-property set and `rowDeltas` in `src/viewport-map.ts`. Items 3, 4 and 5 need the repo section's own CSS (direction, existing hover rules, shade element), so a small reader of the section's styled template is needed.
- figma-section-fields: once the emitter changes, the docs that tell agents to adapt or skip these values by hand should be updated, and the tool copy re-shipped.

## Gaps

- Other project slugs and other machines were not scanned.
- Tool results in the jsonl files are partly missing; the list comes from assistant text in `2ea82aad-7485-4f01-82e9-aec9022c25eb` and `c6c6cc08-0fe0-42e5-bea9-0ad4c826b21b`, and was confirmed by regenerating the overlay from the fixtures.
