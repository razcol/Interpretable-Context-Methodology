# Session extract: OND-7 mobile pass on figma-section-fields

## Request and markers

Find the session where the figma-section-fields workspace was re-run by hand to add the mobile design of OND-7 (ora `ImageGrid`) on top of the desktop section that was already built. Use it, and the sessions around it, to find what the workspace lacks for a desktop-first, then-mobile flow. The findings feed `plan-figma-desktop-mobile.md`.

Markers passed to `scan_transcripts.py` (derived by the agent):

- Pass 1: `OND-7\b`, `(?i)mobile`
- Pass 2: `(?i)mobile (version|design|layout|figma|node)`, `bps\??\.mobile`, `useIsMobile`

## Coverage

- Projects root `/home/dev/.cursor/projects`, 33 slugs.
- Parent transcripts scanned: 797 in each pass. Pass 1 matched 211 files on either marker, and 13 of them on `OND-7`. Pass 2 matched 98.
- Kept: 8 OND-7 sessions (1 core, 6 partial, 1 incidental). Discarded: the 5 other OND-7 hits (rebase, OND-32 font work and commits that only name the branch) and the rest of the pass 2 matches. Example discard: `8a3ae563` (home-dev, LUX-54 filter task), where `bps.mobile` only appears inside repo code the agent read. Other discards: `4a62c031` and `a4ddfbc1` (button `element` runs, desktop only), and `e91763d7` (GraphQL audit for a PR description).
- Subagent files opened: none. The core parent jsonl exists and has no `subagents/` folder.
- Orphan session folders: 4. `home-dev-AI-trading` d4c5d8ad, f219e1ad; `home-dev-colmobil-luxury-trade` 67e77fc8, d54f045e. None are in scope.
- Stores not read: `state.vscdb`, `~/.cursor/chats/*/store.db`, agent-store sqlite. `conversation-search.db` was not used as the search.
- Product path compared: `/home/dev/ai-system/workspaces/figma-section-fields` and the OND-7 worktree `/home/dev/ora-next/.worktrees/OND-7` (HEAD `e52ee8f`).

## Sessions

- `70281275-2703-49a6-b134-7dd8c0b1d462`: home-dev-ai-system, 2026-11-05 13:26, **core**. The manual mobile run of the workspace on node `1482-11000`. User quote: "this is the mobile version of the currently already implemented desktop version. implement this mobile version following that project codebase mobile responsiveness patterns and practices." Path: `~/.cursor/projects/home-dev-ai-system/agent-transcripts/70281275-…/70281275-….jsonl`
- `657777ae-9d58-4a06-8425-8748fd32b578`: home-dev-ora-next, 2026-11-05 14:21, partial. "In OND-7 worktree the chevron is hardocded implemented, does such chevron already exists to use"
- `e4f4439c-6833-475c-bd16-06ad6135b046`: home-dev-ora-next, 2026-11-05 14:22, partial. Commit and push of the mobile pass ("OND-7 worktree- commit the changes and push").
- `2336b3dd-4540-48f8-affe-3e58dad41b9f`: home-dev-ora-next, 2026-11-05 14:25, partial. Video fields dropped from `ImageGrid.gql`, and `CardMedia` now renders images only.
- `69e6c6db-6f89-41a8-b97b-f19b2e30260b`: home-dev-ora-next, 2026-11-05 10:17, partial. Desktop CSS hardening and the "Images are looking strechy" fix (`object-fit: fill` frame crops replaced by cover).
- `35bc612e-bd86-4ea5-a920-a729ce1ed994` and `2e1e06b5-680a-4f36-9068-c6a889530925`: home-dev-ora-next, 2026-11-05 13:00–13:16, partial. The `field-report.md`, a `.gitignore` change and assets were purged from the OND-7 history.
- `e7faf404-1d72-4526-8336-599c4ff6b33f`: home-dev-ora-next, 2026-11-05 13:20, incidental (kept). The OND-7 branch and worktree were restored after an accidental delete. This explains why the commit hashes in `e4f4439c` (`ced0245`) differ from the current branch (`8ccedaa`).

## Keep

- The route the agent chose by hand: `resync` with the stages 01 → 04 → 05, treating the mobile node as an overlay under `theme.bps.mobile` and keeping every desktop rule [70281275].
- The export record linked the two nodes (`desktop source: 3919-20727`). That link is the seed of a pair record [70281275].
- The desktop-to-mobile element mapping was done by content (card titles), not by Figma layer names, and it changed only CSS: grid areas plus `.row { display: contents }`, with the DOM unchanged [70281275].
- No new fields: the `.gql` and `ServerImageGrid.js` stayed untouched because the mobile frame shows the same content [70281275].
- Hover reveal and zoom are gated to `theme.bps.desktop`. On mobile a tap toggles `.is-open`. The agent called this "my call, please confirm", the user committed and pushed it [70281275, e4f4439c].
- Verification at mobile widths (393, 375, 320, plus 768 and 1440 for regression) through an esbuild harness that mounted the real component with media stubbed. The harness also tested taps with `interact.js` [70281275].

## Extra or harmful

- The chevron was drawn as a new inline SVG without first showing the user the repo's icon candidates. The user had to ask in a separate session. `657777ae` found no matching shared icon, so the inline icon stayed, but the search should have come before drawing [657777ae].
- The mobile rules went into one block at the end of `StyledImageGrid.js`. In the five repos, 81–90% of `bps.mobile` blocks in `Styled*.js` sit inside a child selector rather than at the component's root level (see the plan's pattern map). The block works, but it is not the dominant repo style [70281275, current code].
- The workspace makes `field-report.md` a non-ignored file beside the component. On OND-7 the user then had to purge it, and a `.gitignore` edit, from the branch history [35bc612e]. This is not a mobile issue, but a mobile pass that reuses the same folder rule will hit it again.

## Still missing

1. **No way to say "this URL is the mobile design of that section".** Still open. The triggers (`new`, `sync`, `resync`, `element`) take one Figma URL, and a run is keyed by one node id. The agent reasoned that "a straightforward resync with drift mode would wrongly treat the mobile design as the base layout" [70281275].
2. **Stage 04 has no mobile mode.** Still open. `binding-rules.md` resync says the new scaffold is "the design truth for structure and styles". For a mobile node, applying that would overwrite desktop. The agent had to invent the "mobile overlay" rule [70281275].
3. **Stage 05 widths are desktop only (1920, 1440, 1100).** Still open. The agent swapped in 393/375/320 by hand. It also noticed that ora's `theme.bps.desktop` is `min-width: 1279px` while `bps.mobile` is `max-width: 1279px`, so both apply at exactly 1279px [70281275, current `ora-next/code/app/styles/theme/index.js`].
4. **No mobile pattern reference.** Still open. The agent rediscovered `theme.bps`, `useIsMobile`, the icon conventions and `QuestionAnswerItem` with about 12 greps [70281275].
5. **No hover-to-touch rule with a checkpoint.** Partly open. The checklist row "Hover-only content has a touch fallback" exists, but it has no pattern or decision point, so the agent made the call alone [70281275].
6. **Level 2 cannot run in a worktree with no `node_modules` or DB access.** Still open. It was skipped on both 1404-7715 and 1482-11000. The improvised esbuild harness is the only in-browser check of the real component [70281275].
7. **Desktop is never checked for regressions after a mobile pass.** Still open. The 1440 harness shot was a by-eye check only [70281275].

## Out of scope

- Dropping video fields from fragments a component never renders [2336b3dd]. This is a fragment-scope rule, not a mobile one.
- The `object-fit: fill` stretch on the desktop frame crops [69e6c6db]. Already fixed in `5242142`.
- Branch hygiene: purging assets, `.gitignore` edits and the restore [2e1e06b5, 35bc612e, e7faf404].

## Implications

Recommendations only. The detailed plan is `plan-figma-desktop-mobile.md`.

- **figma-section-fields `CLAUDE.md`**: add a `mobile <Folder> <mobile-url> <repo>` trigger and an optional `--mobile <url>` on `new` and `sync`. Desktop first, then mobile. Never derive a mobile node from the desktop one.
- **`shared/run-records.md`**: add `viewport` and `pair` lines so the desktop and mobile node folders point at each other, and so `status` shows them as one pair.
- **Stage 01**: in mobile mode, write a `viewport-map.md` (mobile element → desktop class, order, size, visible/hidden/new) as a human edit surface, with a checkpoint.
- **Stage 04 `binding-rules.md`**: add a `mobile: overlay` section. Desktop rules are frozen, mobile deltas are nested `theme.bps.mobile` blocks, hover has a touch fallback after a checkpoint, and icons are searched in the repo before drawing one.
- **Stage 05 `verify-steps.md`**: mobile widths 320/375/<Figma width>/768/1279, the 1279/1280 boundary, a desktop regression diff at 1440, and a tap check.
- **next-section-repo skill**: a `mobile-patterns.md` reference, probe keys for the breakpoints, the mobile hook and responsive image, a `bps` overlap warning, and a promoted harness script.

## Gaps

- Tool results are mostly absent from the jsonl. Outcomes were confirmed from later assistant text, from the run records in `stages/0{1,4,5}-*/output/1482-11000/`, and from `git log` on the OND-7 worktree.
- Sessions from the Windows Cursor profile (`mnt-c-Users-raz-c*` slugs were scanned, but a separate Windows-side `.cursor` was not) and from other machines are not included.
- A mobile pass on another repo phrased without the word "mobile" (for example "responsive" or "רספונסיבי") would be missed by these markers.
