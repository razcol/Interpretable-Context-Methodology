# figma-cli

The exporter is the single executable `tools/figma-cli`. Do not clone a project and do not run npm in this workspace. Replace that file only when a new shipped binary is provided.

## Runtime

Needs Node >= 20 on `PATH`. The file starts with `#!/usr/bin/env node`.

Verify from `workspaces/figma-section-fields`:

```
tools/figma-cli help
```

## Token

Set `FIGMA_ACCESS_TOKEN` in the environment before export. Do not store the token in a file, a record, or a committed command.

## Export

This workspace always exports with `--dist`. File names, flags, and exit codes are in `shared/export-contract.md`.
