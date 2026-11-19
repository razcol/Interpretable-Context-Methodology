# Onboarding Questionnaire

Read this file when the user types `setup`. Ask ALL questions below in one pass, so the user can answer everything in one message. Replace the placeholders in the files listed, then scan the workspace for any `{{` left.

Before the questions, run `python3 ../../_core/data-root/data_root.py init` from this workspace folder. It creates your data root (default `~/.config/ai-system`) when it is missing and changes nothing when it is complete. See "Data root" in `_core/CONVENTIONS.md`.

These questions configure the workspace. Per-run facts (Figma URL, repo for this run, folder name, target file for `element`) come with the trigger.

### Q1: Which section repos does this workspace write into, and where are they?
- Files: `<data-root>/workspaces/figma-section-fields/repos.md` (when it does not exist, start from `targets/repos.example.md`). One row per repo; never write a repo's facts into a file of this repo.
- Type: free text, `name = path` per line (the repo root or its `code/` folder), to add or change rows
- Default: the rows already in the table stay as they are. A new row starts with test route "none yet".

### Q2: Which repo should a run use when it does not name one?
- Files: `<data-root>/workspaces/figma-section-fields/repos.md` (when it does not exist, start from `targets/repos.example.md`)
- Type: selection: one of the repo names in the table
- Default: the default the table already names; with none yet, the first row

### Q3: Which file holds the Figma token?
- Files: `<data-root>/workspaces/figma-section-fields/repos.md`, its "Figma token file" line (when the file does not exist, start from `targets/repos.example.md`). Never write the path into a file of this repo.
- Type: free text, the path of an env file with a `FIGMA_ACCESS_TOKEN=` line (record the path only; never open the file)
- Default: the path the line already names; with none yet, `~/cli/figma-cli/.env`

### Q4: Which local page should stage 05 open to see a section in the app, per repo?
- Files: `<data-root>/workspaces/figma-section-fields/repos.md` (when it does not exist, start from `targets/repos.example.md`)
- Type: free text, `name = /path/` per line: a path on the dev server where your test page lists the sections you are building
- Default: the routes already in the table.
- Derived: other repos start with "none yet". Stage 05 asks for a route the first time it runs on one of them and adds it to `<data-root>/workspaces/figma-section-fields/repos.md`.

---

## After Onboarding

Tell the user which values were written. Runs start with a trigger from `CLAUDE.md`, for example `new '<figma-url>' <repo name>`.
