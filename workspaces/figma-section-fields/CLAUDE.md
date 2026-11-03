# Figma Section Fields

Turn a Figma layer into a section of one of your Next.js + styled-components + WPGraphQL/ACF repos: a Server/Client component in the repo's own shape, a `.gql` fragment from the live WordPress schema, and props bound to it, checked in a browser.

## Folder Map

```
figma-section-fields/
├── CLAUDE.md, CONTEXT.md
├── setup/questionnaire.md        (onboarding)
├── targets/repos.md              (repo roots, test routes)
├── shared/                       (export contract, figma-cli setup, run records)
├── skills/next-section-repo/     (repo probe, section checker, section shape)
├── tools/figma-cli               (shipped exporter)
└── stages/
    ├── 01-export/        (probe the repo, inspect, render, scaffold into staging)
    ├── 02-field-plan/    (field plan and field-report.md; stops for you on new)
    ├── 03-fragment/      (the .gql from the live group)
    ├── 04-conform-bind/  (staging scaffold into the repo, bound to the fragment)
    └── 05-verify/        (preview against Figma, overflow in the app)
```

## Triggers

| Keyword | Action |
|---------|--------|
| `setup` | Run the onboarding questionnaire |
| `status` | List runs. See below |
| `new <figma-url> <repo>` | New section. 01, 02, then stop until you build the ACF group |
| `continue <node-id>` | After you saved the group: 03, 04, 05 for that run |
| `sync <Folder> <figma-url> <repo>` | The ACF group already exists. 01, 02 (compare only), 03, 04, 05 |
| `resync <Folder> <figma-url> <repo>` | Design or exporter changed. 01, 04 (drift mode), 05 |
| `element <figma-url> <repo> <file>` | Restyle one existing control. 01 (inspect only), 04 (element mode) |

A run is keyed by the Figma node id. Its records live in `stages/0N-*/output/<node-id>/` (see `shared/run-records.md`).

### How `status` works

List each `<node-id>` folder under `stages/01-export/output/`. For each, read `route` and `folder` from its `export-record.md`, then mark every stage on that route COMPLETE when its record exists in `stages/0N-*/output/<node-id>/`, otherwise PENDING. A `new` run with a field plan and no fragment record is "02 waiting for you". Say when the section folder named in the record no longer exists.

```
Run <node-id> (<route>, <Folder>, <repo>)
  [01-export] --> [02-field-plan] --> [03-fragment] --> [04-conform-bind] --> [05-verify]
     STATUS          STATUS              STATUS            STATUS              STATUS
```

## Routing

| Task | Go To |
|------|-------|
| Any route, first step | `stages/01-export/CONTEXT.md` |
| Field plan and field report | `stages/02-field-plan/CONTEXT.md` |
| Fragment | `stages/03-fragment/CONTEXT.md` |
| Repo files and binding | `stages/04-conform-bind/CONTEXT.md` |
| Browser check | `stages/05-verify/CONTEXT.md` |
| Which repo and route | `targets/repos.md` |

## What to Load

| Stage | Load These | Do NOT Load |
|-------|-----------|-------------|
| 01 | Its CONTEXT, `shared/export-contract.md`, `shared/figma-cli-setup.md`, `targets/repos.md`, the next-section-repo SKILL | Later stages, figma-cli source |
| 02 | Its CONTEXT and references, the run's export record and profile, the wp-graphql SKILL | Stage 03 to 05 files, other runs' outputs |
| 03 | Its CONTEXT and reference, the run's field plan and profile, the wp-graphql SKILL | Stage 04 and 05 files, the field report |
| 04 | Its CONTEXT and reference, the run's records and `.gql`, the next-section-repo SKILL and checklist | wp-graphql internals, other runs |
| 05 | Its CONTEXT and reference, the run's records, the browser-cdp SKILL | Stage 02 and 03 references |

## Stage Handoffs

Each stage writes its record into `output/<node-id>/` and, on the same run, loads the next stage on its route. The run stops only where a route says so (`new` after 02), when 02 or 03 finds the live group differs from the plan, when export exits 9 or 10, or when 05 fails twice. Later stages read earlier records. Earlier stages never read later ones. Records are run history, not templates.

## Ground Rules

- No desktop, screen or computer-use tools. Headless browser only, through browser-cdp.
- WordPress is read only through the wp-graphql skill. Never write a query, sign in by hand, or read the store or cache.
- The live schema and the repo files win over saved records. Re-read them at each stage.
- The Figma token is loaded with `node --env-file`. Never print it, paste it into a command, or write it to a file. If you paste a token into chat, rotate it.
- On `new`, never bind or write a fragment before you say the ACF group is saved.
- Never edit a repo's main working tree when the user named a worktree. Never push.
