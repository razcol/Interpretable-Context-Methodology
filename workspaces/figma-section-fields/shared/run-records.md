# Run records

A run is one Figma node on one route. Its key is the node id with `:` written as `-` (`1404-7715`). Every stage writes into `stages/0N-*/output/<node-id>/`, so two runs on different sections never overwrite each other. A second run on the same node replaces that node's records.

Output folders are git-ignored. Records are history for `status` and for the next stage of the same run. They are not templates: a stage never reads another run's records.

## Records

| Stage | Files in `output/<node-id>/` | Holds |
|---|---|---|
| 01 | `export-record.md`, `profile.json`, `inspect.txt`, `figma.png`, `preview.html`, `scaffold/<Folder>/` | Route, Figma URL, node id, repo, app root, folder, figma-cli `--version` line, flags, every `note:` line |
| 02 | `field-plan.md`, `field-plan.json` | The plan you approved or are reviewing, the questions and your answers |
| 03 | `fragment-record.md` | The `.gql` path, `diff-group` result, `check-fragment` summary |
| 04 | `conform-record.md` | Files written or changed, the binding table, drift applied, `check_section` result |
| 05 | `verify-report.md`, `shots/` | Level 1 diff ratio, Level 2 widths and overflow, PASS or FAIL |

`field-report.md` is not a record. It sits beside the component in the repo (stage 02) as a helper you delete later. It is not git-ignored.

## export-record.md

```markdown
# Export record <node-id>
- route: new | sync | resync | element
- figma: <url>
- node: <node-id>
- repo: <repo root>   app: <app root>
- folder: <Folder>    section path: <app root>/<sectionsDir>/<Folder>
- target file (element only): <path>
- figma-cli: <output of --version>
- flags: <scaffold flags used>
- notes: <each note: line, or none>
```

Later records start with the same `# <Stage> record <node-id>` line and list facts as bullets, then tables.
