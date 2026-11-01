# Skill Index

Registry of every skill this workspace has built or maintains. Updated by `stages/06-publish` whenever a skill is published or re-published. Checked by `stages/01-intake` first when resolving existing-skill requests.

| Name | Location | Purpose | Status |
|------|----------|---------|--------|
| browser-cdp | `_core/skills/browser-cdp/` | Deterministic JSON scripts to drive Chrome over CDP: screenshots, baseline diffs, DOM/a11y/text snapshots, console and network capture, interaction, cookies and storage | active (provisional: WSL Chrome headless tested) |
| session-handoff | `_core/skills/session-handoff/` | On request, writes a self-contained handoff document (11 fixed sections) from the current session so unfinished work can be continued in a session without the conversation. Helper scripts gather system facts and check structure and secrets | active (tested once: one task, fresh-reader check; non-code task not yet tested) |
| system-flowcharts | `_core/skills/system-flowcharts/` | Plan a flowchart, then generate a deterministic editable Excalidraw file (plus SVG and PNG) from a spec or Mermaid. Layout is elkjs or mermaid-to-excalidraw; the agent does not hand-place coordinates | active (approved 2026-10-28, tested on the skill-factory pipeline and an order-fulfillment flow) |
| wp-graphql | `_core/skills/wp-graphql/` | Fixed commands for a Next app's WordPress GraphQL schema: section patterns, where a section is attached, its field tree, and a `.gql` check | active (approved 2026-10-29 after a live ora-next section task) |
| session-extract | `_core/skills/session-extract/` (mirrored at `~/.cursor/skills/session-extract/`) | Search past Cursor sessions on this machine across projects, filter for a tool or workflow, and write a cited brief for changing skills, tools, or workspaces | active (approved 2026-11-01 after a figma-cli corpus test) |

## Status values

- `active` -- in use, considered current
- `deprecated` -- superseded or no longer recommended, kept for reference
