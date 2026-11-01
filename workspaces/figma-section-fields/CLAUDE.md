# Figma Section Fields

Turn one Figma layer into a React + styled-components section, a GraphQL fragment for the Jaecoo or luxury-trade ACF flexible field, and a component whose content reads those fields.

## Folder Map

```
figma-section-fields/
├── CLAUDE.md
├── CONTEXT.md             (task routing)
├── setup/
│   └── questionnaire.md   (onboarding)
├── targets/
│   ├── CONTEXT.md
│   └── repos.md           (repo paths, filled at setup)
├── shared/
│   └── export-contract.md (figma-cli --dist output)
├── skills/
│   └── acf-section-fields/  (audit, fragment patterns, scripts)
├── tools/
│   └── figma-cli            (shipped executable; export one layer to a folder)
└── stages/
    ├── 01-figma-export/     (Figma layer to component files)
    ├── 02-section-graphql/  (component files to a .gql fragment)
    └── 03-field-migration/  (fragment fields bound into the component)
```

## Triggers

| Keyword | Action |
|---------|--------|
| `setup` | Run the onboarding questionnaire |
| `status` | Show pipeline completion for all stages |

### How `status` works

For stage 01 and stage 03, scan that stage's `output/` folder. Ignore `.gitkeep`. Any other file is COMPLETE. No other file is PENDING.

Stage 02 does not write its `output/` folder. It is COMPLETE when the folder named in `stages/01-figma-export/output/export-record.md` contains `<Folder>.gql` and `field-report.md`. It is PENDING when that record is missing or those two files are missing.

Render:

```
Pipeline Status: figma-section-fields

  [01-figma-export]  -->  [02-section-graphql]  -->  [03-field-migration]
        STATUS                     STATUS                    STATUS
```

Replace each STATUS with COMPLETE or PENDING.

## Routing

| Task | Go To |
|------|-------|
| Export a Figma layer | `stages/01-figma-export/CONTEXT.md` |
| Write the section fragment | `stages/02-section-graphql/CONTEXT.md` |
| Bind fields into the component | `stages/03-field-migration/CONTEXT.md` |
| Resolve which repo to write into | `targets/CONTEXT.md` |

## What to Load

| Task | Load These | Do NOT Load |
|------|-----------|-------------|
| Export a layer | `stages/01-figma-export/CONTEXT.md`, `shared/export-contract.md`, `stages/01-figma-export/references/figma-cli-setup.md`, `targets/repos.md` | Stage 02 and stage 03 files until the export record exists. Then load stage 02. The repo that is not the chosen project |
| Write the fragment | `stages/02-section-graphql/CONTEXT.md`, `stages/01-figma-export/output/export-record.md`, `_core/skills/wp-graphql/SKILL.md`, `stages/02-section-graphql/references/graphql-stage.md` | Stage 03 files until `<Folder>.gql` and `field-report.md` exist in the section folder. Then load stage 03. `skills/acf-section-fields/`, `tools/figma-cli` source, the other site's repo |
| Bind fields | `stages/03-field-migration/CONTEXT.md`, `stages/01-figma-export/output/export-record.md`, `<export-dir>/<Folder>/<Folder>.gql`, `stages/03-field-migration/references/migration-rules.md` | `tools/figma-cli`, the other site's repo, `field-report.md`, `skills/acf-section-fields/` |

## Stage Handoffs

A run is the whole pipeline. Stage 01 writes `stages/01-figma-export/output/export-record.md` and the component folder, then the same run loads stage 02. Stage 02 writes `<export-dir>/<Folder>/<Folder>.gql` and `<export-dir>/<Folder>/field-report.md`, then the same run loads stage 03. Stage 03 binds that fragment into the component and writes `stages/03-field-migration/output/migration-record.md`. Do not end the run between stages. Stop only when a required input is missing, or when export exit 9 or 10 asks the human to pick a layer.

Later stages read earlier outputs. Earlier stages do not read later stages.

`tools/figma-cli` is the shipped exporter. Run it; do not read it as source. Stage 02 reads the live schema through the wp-graphql skill named in its CONTEXT. `skills/acf-section-fields` is the Jaecoo and luxury-trade field guide. Load a skill file only when the stage CONTEXT names it.
