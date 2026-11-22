# Figma Section Fields

Turn a Figma layer into a section of one of your Next.js + styled-components + WPGraphQL/ACF repos: a Server/Client component in the repo's own shape, a `.gql` fragment from the live WordPress schema, and props bound to it, checked in a browser.

## Folder Map

```
figma-section-fields/
├── CLAUDE.md, CONTEXT.md
├── setup/questionnaire.md        (onboarding)
├── targets/repos.example.md              (example repo table: roots, default repo, test routes)
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
| `status` | List runs (a desktop and mobile pair shows as one block), and the runs that hold a claim now |
| `new <figma-url> <repo> [--mobile <url>]` | New section. 01, 02, then stop until you build the ACF group. With `--mobile`, the mobile pass follows desktop 05 |
| `continue <node-id>` | After you saved the group: 03, 04, 05 for that run |
| `sync <Folder> <figma-url> <repo> [--mobile <url>]` | The ACF group already exists. 01, 02 (compare only), 03, 04, 05. With `--mobile`, the mobile pass follows desktop 05 |
| `mobile <Folder> <mobile-url> <repo>` | Mobile design for a section whose desktop is built: 01m, 04m, 05m |
| `resync <Folder> <figma-url> <repo> [--mobile]` | Design or exporter changed. 01, 04 (drift mode), 05. `--mobile` resyncs the mobile pass only |
| `element <figma-url> <repo> <file> [--mobile]` | Restyle one existing control. 01 (inspect only), 04 (element mode). `--mobile` edits only in `bps.mobile` blocks |

A run is keyed by the Figma node id. Its records live in `<runs>/<node-id>/0N-*/` in the data root. A mobile pass is its own run, linked to the desktop run by `pair:` lines. How `status` works and what each record holds: `shared/run-records.md`.

`<data-root>` in this workspace's files is your data folder, outside the repo: the path `python3 ../../_core/data-root/data_root.py resolve` prints from this workspace folder (see "Data root" in `../../_core/CONVENTIONS.md`). `<runs>` is `<data-root>/workspaces/figma-section-fields/runs`, the run folders (never `stages/*/output/` in this repo). `<checkout>` is the ai-system checkout this run is in: the path `python3 ../../_core/data-root/data_root.py checkout` prints from this workspace folder. `<workspace>` is `<checkout>/workspaces/figma-section-fields`. Tool paths in the stage files (`$FIGMA`, browser-cdp, the harness) start at `<workspace>` or `<checkout>`, so a run uses the tools of the checkout it runs in, never another checkout's. Resolve all of them once per run, with the full `$FIGMA` value (`shared/figma-cli-setup.md`: `<workspace>` plus the "Figma token file" line of the repo table), and use the real paths in every brief and command.

Runs on different node ids run at the same time; only what they share is claimed ("Run claims" in `../../_core/CONVENTIONS.md`). `C` is `python3 ../../_core/data-root/run_claim.py` from this workspace folder:

1. Before a route's first stage: `C claim --ws figma-section-fields --key <node-id> --note <route>`, and the same for M when the route includes a mobile pass. Keep each `claimId`. Exit 3 means a live run holds that node id: stop and name the claim it reports. A `staleCleared` line means an earlier run was killed: say so and continue from its records. Only when you say that run is not running, claim again with `--takeover`.
2. Before stage 01 writes anything into the repo: `C target --ws figma-section-fields --key <node-id> --path <repo work tree> --root <repo root> --branch <its current branch>`. Exit 3 means another run edits that work tree or branch: stop and name it (a worktree of the repo, named in the run, avoids the clash).
3. After each stage writes its record: `C commit --ws figma-section-fields --key <node-id> --stage <0N-name>`. It commits only that run's folder.
4. When the route stops (its last stage, a checkpoint, a second FAIL, an export exit): `C end --ws figma-section-fields --key <node-id> --claim-id <claimId>` for each key it claimed, in its own shell call, never chained after `commit` with `&&`. `release --token` is the deprecated name of `end --claim-id`; do not use it.

Stage 05 takes the run's own dev and browser ports and browser profile from the claim (`stages/05-verify/references/verify-steps.md` "Run ports and browser"). No `.run-lock` file is written anywhere.

## Routing

| Task | Go To |
|------|-------|
| Any route, first step | `stages/01-export/CONTEXT.md` |
| Field plan and field report | `stages/02-field-plan/CONTEXT.md` |
| Fragment | `stages/03-fragment/CONTEXT.md` |
| Repo files and binding | `stages/04-conform-bind/CONTEXT.md` |
| Browser check | `stages/05-verify/CONTEXT.md` |
| Which repo and route | `<data-root>/workspaces/figma-section-fields/repos.md`, read as `targets/CONTEXT.md` "Rules" says |

## What to Load

| Stage | Load These | Do NOT Load |
|-------|-----------|-------------|
| 01 | Its CONTEXT, `shared/export-contract.md`, `shared/figma-cli-setup.md`, `shared/run-records.md`, `<data-root>/workspaces/figma-section-fields/repos.md`, `targets/CONTEXT.md` "Rules", the next-section-repo SKILL | Later stages, figma-cli source |
| 01m | Its CONTEXT, `shared/export-contract.md`, `shared/figma-cli-setup.md`, `shared/run-records.md`, `<data-root>/workspaces/figma-section-fields/repos.md`, `targets/CONTEXT.md` "Rules", `stages/01-export/references/viewport-map.md`, D's records, the next-section-repo SKILL and `references/mobile-patterns.md` | Later stages, figma-cli source |
| 02 | Its CONTEXT and references, the run's export record and profile, the wp-graphql SKILL | Stage 03 to 05 files, other runs' outputs (except the paired M's `inspect.txt` and `figma.png`) |
| 03 | Its CONTEXT and reference, the run's field plan and profile, the wp-graphql SKILL | Stage 04 and 05 files, the field report |
| 04 | Its CONTEXT and reference, the run's records and `.gql`, the next-section-repo SKILL and checklist | wp-graphql internals, other runs |
| 04m | Its CONTEXT, the "mobile: overlay" and "Record" sections of `binding-rules.md`, `mobile-patterns.md`, the run's export record, viewport map and overlay, the next-section-repo SKILL and checklist | Stage 02 and 03 references |
| 05 | Its CONTEXT and reference, the run's records, the browser-cdp SKILL | Stage 02 and 03 references |
| 05m | Its CONTEXT, the Mobile section of `verify-steps.md`, the run's records, `<data-root>/workspaces/figma-section-fields/repos.md`, the browser-cdp SKILL | Stage 02 and 03 references |

## Stage Handoffs

Each stage writes its record into `<runs>/<node-id>/0N-*/` and, on the same run, loads the next stage on its route. The run stops only where a route says so (`new` after 02), when 02 or 03 finds the live group differs from the plan, when export exits 9 or 10, or when 05 fails twice. Later stages read earlier records. Earlier stages never read later ones. Records are run history, not templates.

## Ground Rules

- No desktop, screen or computer-use tools. Headless browser only, through browser-cdp.
- WordPress is read only through the wp-graphql skill. Never write a query, sign in by hand, or read the store or cache.
- The live schema and the repo files win over saved records. Re-read them at each stage.
- The Figma token is loaded with `node --env-file`. Never print it, paste it into a command, or write it to a file. If you paste a token into chat, rotate it.
- On `new`, never bind or write a fragment before you say the ACF group is saved.
- Never edit a repo's main working tree when the user named a worktree, and never a work tree this run has not claimed. Never push.
- One repo per run, from `<data-root>/workspaces/figma-section-fields/repos.md`, read with `targets/CONTEXT.md` "Rules" (default repo, worktree roots). Each repo has its own WordPress and its own fields.
- Never derive a mobile design from a desktop frame or the reverse. A mobile pass needs the mobile URL from the user.
- The mobile touch path comes from the mobile frame ([mobile-patterns.md "Hover and touch"](skills/next-section-repo/references/mobile-patterns.md#hover-and-touch)).
