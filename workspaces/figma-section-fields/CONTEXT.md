# Figma Section Fields

One Figma layer becomes a section in one of your Next.js repos: the repo's Server/Client files, a `.gql` fragment from the live ACF group, and props bound to it. Triggers and routes are in `CLAUDE.md`.

## Task Routing

| Task Type | Go To | Description |
|-----------|-------|-------------|
| Start any route | `stages/01-export/CONTEXT.md` | Probe the repo, inspect and render the layer, scaffold into staging |
| Plan the fields | `stages/02-field-plan/CONTEXT.md` | Field plan, field report beside the component, stop on `new` |
| Write the fragment | `stages/03-fragment/CONTEXT.md` | `.gql` from the live group, checked |
| Put it in the repo | `stages/04-conform-bind/CONTEXT.md` | Copy the scaffold, bind fields, resync drift, element edits |
| Check it rendered | `stages/05-verify/CONTEXT.md` | Preview against Figma, overflow at three widths |
| Add the mobile design to a built section | `stages/01-export/CONTEXT.md` (mobile route) | Mobile pass: 01m viewport map and overlay, 04m, 05m |

## Shared Resources

| Resource | Location | Contains |
|----------|----------|----------|
| Target repos | `targets/repos.md` | Repo roots, default repo, test routes |
| Export contract | `shared/export-contract.md` | figma-cli commands, flags, files and exit codes |
| figma-cli setup | `shared/figma-cli-setup.md` | How to call the shipped binary and load the token |
| Run records | `shared/run-records.md` | Per-run folders, what each record holds, desktop and mobile pairs, `status` |
| Repo skill | `skills/next-section-repo/SKILL.md` | Repo profile and section checker |
| WP GraphQL | `../../_core/skills/wp-graphql/SKILL.md` | Live schema, fragment checks, `diff-group` |
| Browser | `../../_core/skills/browser-cdp/SKILL.md` | Screenshots, diffs, `measure.js` |
