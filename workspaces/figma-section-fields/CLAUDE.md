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
    ├── 01-export/        (probe the repo, inspect, render, scaffold into staging; mobile overlay via figma-cli)
    ├── 02-field-plan/    (field plan and field-report.md; stops for you on new)
    ├── 03-fragment/      (the .gql from the live group)
    ├── 04-conform-bind/  (staging scaffold into the repo, bound to the fragment)
    └── 05-verify/        (preview against Figma, overflow in the app)
```

## Triggers

| Keyword | Action |
|---------|--------|
| `setup` | Run the onboarding questionnaire |
| `status` | List runs. A desktop and mobile pair shows as one block |
| `new <figma-url> <repo> [--mobile <url>]` | New section. 01, 02, then stop until you build the ACF group. With `--mobile`, the mobile pass follows desktop 05 |
| `continue <node-id>` | After you saved the group: 03, 04, 05 for that run |
| `sync <Folder> <figma-url> <repo> [--mobile <url>]` | The ACF group already exists. 01, 02 (compare only), 03, 04, 05. With `--mobile`, the mobile pass follows desktop 05 |
| `mobile <Folder> <mobile-url> <repo>` | Mobile design for a section whose desktop is built: 01m, 04m, 05m |
| `resync <Folder> <figma-url> <repo> [--mobile]` | Design or exporter changed. 01, 04 (drift mode), 05. `--mobile` resyncs the mobile pass only |
| `element <figma-url> <repo> <file> [--mobile]` | Restyle one existing control. 01 (inspect only), 04 (element mode). `--mobile` edits only in `bps.mobile` blocks |

A run is keyed by the Figma node id. Its records live in `stages/0N-*/output/<node-id>/`. A mobile pass is its own run, linked to the desktop run by `pair:` lines. How `status` works and what each record holds: `shared/run-records.md`.

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
| 01m | Its CONTEXT, `shared/export-contract.md`, `shared/figma-cli-setup.md`, `stages/01-export/references/viewport-map.md`, the next-section-repo SKILL and `references/mobile-patterns.md` | Later stages, figma-cli source |
| 02 | Its CONTEXT and references, the run's export record and profile, the wp-graphql SKILL | Stage 03 to 05 files, other runs' outputs (except the paired M's `inspect.txt` and `figma.png`) |
| 03 | Its CONTEXT and reference, the run's field plan and profile, the wp-graphql SKILL | Stage 04 and 05 files, the field report |
| 04 | Its CONTEXT and reference, the run's records and `.gql`, the next-section-repo SKILL and checklist | wp-graphql internals, other runs |
| 04m | Its CONTEXT, the mobile section of `binding-rules.md`, `mobile-patterns.md`, the run's viewport map and overlay | Stage 02 and 03 references |
| 05 | Its CONTEXT and reference, the run's records, the browser-cdp SKILL | Stage 02 and 03 references |
| 05m | Its CONTEXT, the Mobile section of `verify-steps.md`, the browser-cdp SKILL | Stage 02 and 03 references |

## Stage Handoffs

Each stage writes its record into `output/<node-id>/` and, on the same run, loads the next stage on its route. The run stops only where a route says so (`new` after 02), when 02 or 03 finds the live group differs from the plan, when export exits 9 or 10, or when 05 fails twice. Later stages read earlier records. Earlier stages never read later ones. Records are run history, not templates.

## Ground Rules

- No desktop, screen or computer-use tools. Headless browser only, through browser-cdp.
- WordPress is read only through the wp-graphql skill. Never write a query, sign in by hand, or read the store or cache.
- The live schema and the repo files win over saved records. Re-read them at each stage.
- The Figma token is loaded with `node --env-file`. Never print it, paste it into a command, or write it to a file. If you paste a token into chat, rotate it.
- On `new`, never bind or write a fragment before you say the ACF group is saved.
- Never edit a repo's main working tree when the user named a worktree. Never push.
- Never derive a mobile design from a desktop frame or the reverse. A mobile pass needs the mobile URL from the user.
- The mobile touch path comes from the mobile frame ([mobile-patterns.md "Hover and touch"](skills/next-section-repo/references/mobile-patterns.md#hover-and-touch)).
