# Skill Index

Registry of every skill this workspace has built or maintains. Updated by `stages/06-publish` whenever a skill is published or re-published. Checked by `stages/01-intake` first when resolving existing-skill requests.

| Name | Location | Purpose | Status |
|------|----------|---------|--------|
| browser-cdp | `_core/skills/browser-cdp/` | Deterministic JSON scripts to drive Chrome over CDP: screenshots, baseline diffs, horizontal overflow at set viewports (measure.js), DOM/a11y/text snapshots, console and network capture, interaction, cookies and storage | active (provisional: WSL Chrome headless tested) |
| session-handoff | `_core/skills/session-handoff/` | On request, writes a self-contained handoff document (11 fixed sections) from the current session so unfinished work can be continued in a session without the conversation. Helper scripts gather system facts and check structure and secrets | active (tested once: one task, fresh-reader check; non-code task not yet tested) |
| system-flowcharts | `_core/skills/system-flowcharts/` | Plan a flowchart, then generate a deterministic editable Excalidraw file (plus SVG and PNG) from a spec or Mermaid. Layout is elkjs or mermaid-to-excalidraw; the agent does not hand-place coordinates | active (approved 2026-10-28, tested on the skill-factory pipeline and an order-fulfillment flow) |
| wp-graphql | `_core/skills/wp-graphql/` | Fixed commands for a Next app's WordPress GraphQL schema: section patterns, where a section is attached, its field tree, `.gql` checks that accept the repos' shared media spreads, and `diff-group` to compare a field plan with the live group | active (approved 2026-10-29; updated 2026-11-03, 33 offline tests, check-repo run on all five repos) |
| session-extract | `_core/skills/session-extract/` (mirrored at `~/.cursor/skills/session-extract/`) | Search past Cursor sessions on this machine across projects, filter for a tool or workflow, and return a cited brief in the chat for changing skills, tools, or workspaces | active (approved 2026-11-01 after a figma-cli corpus test; 2026-11-08: brief stays in the chat) |
| session-debrief | `_core/skills/session-debrief/` | Explains one Cursor or Kiro CLI session to the person who must decide: the answer first, how it works, each open decision with a recommendation, what was left undone, and the follow-up questions already answered | active (approved 2026-11-08; Rovo retest 6.5/7, 68 script tests) |

## Status values

- `active` -- in use, considered current
- `deprecated` -- superseded or no longer recommended, kept for reference
