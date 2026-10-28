# Stage 01: Figma Export

Export one Figma layer into a project folder with the bundled CLI.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Run | User message | Figma file or URL, node id, target project, export directory | Required before any command |
| Targets | `../../targets/repos.md` | Full file | Resolve the project and sections directory |
| Contract | `../../shared/export-contract.md` | Full file | Output shape and exit codes |
| Setup | `references/figma-cli-setup.md` | Full file | Node, token, and how to call the CLI |

## Process

1. Collect the Figma file or URL, node id, target project, and the directory inside that project to write into. All four are required. Stop if the project or the export path is missing.
2. Resolve the project from `../../targets/repos.md`. The export directory must sit inside that repo.
3. Follow `references/figma-cli-setup.md`. The exporter is the executable `tools/figma-cli`. The token is `FIGMA_ACCESS_TOKEN` in the environment. Never write the token into a file.
4. From `workspaces/figma-section-fields`, run `tools/figma-cli export <file> <node-id> --dist <export-dir>`. Always `--dist`. Never `--stdout` or `--dump`. Add `--name` or `--exclude` only if the user asked.
5. On exit 9 or exit 10, stop at the checkpoint. Do not write the record until the user picks a layer.
6. Confirm `<export-dir>/<PascalCaseName>/index.js`, `<Name>.js`, `Styled<Name>.js`, and `assets/` when the layer has images.
7. Run the audit. Write `output/export-record.md` with the file, node id, component name, and the folder that was written.
8. Continue this run. Load `../02-section-graphql/CONTEXT.md` and follow it. Do not end the run after the export record.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 5 | Paths from exit 10 (same name) or exit 9 (no match) | Which layer to export |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Sources | `index.js`, `<Name>.js`, and `Styled<Name>.js` exist |
| Styled name | The styled file is `Styled<Name>.js` |
| Path | The export folder is inside the chosen repo |
| Record | `output/export-record.md` names that same folder |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Export record | `output/export-record.md` | File, node id, component name, folder written |
| Component files | `<export-dir>/<PascalCaseName>/` | CLI `--dist` output |
