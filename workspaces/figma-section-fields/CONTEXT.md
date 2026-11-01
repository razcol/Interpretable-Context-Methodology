# Figma Section Fields

One Figma layer becomes a section component, a GraphQL fragment, and props bound to that fragment.

## Task Routing

| Task Type | Go To | Description |
|-----------|-------|-------------|
| Export a layer | `stages/01-figma-export/CONTEXT.md` | Run figma-cli into the chosen project |
| Write the fragment | `stages/02-section-graphql/CONTEXT.md` | Write the `.gql` from the live schema |
| Bind the fields | `stages/03-field-migration/CONTEXT.md` | Read fragment fields from the component |

## Shared Resources

| Resource | Location | Contains |
|----------|----------|----------|
| Target repos | `targets/CONTEXT.md` | Which project and sections directory to use |
| Export contract | `shared/export-contract.md` | `--dist` file names and CLI exit codes |
| figma-cli | `tools/figma-cli` | Shipped exporter. Contract: `shared/export-contract.md` |
| ACF skill | `skills/acf-section-fields/SKILL.md` | Jaecoo and luxury-trade field audit. Stage 02 does not load it |
| WP GraphQL | `../../_core/skills/wp-graphql/SKILL.md` | Live schema commands for the `.gql` |
