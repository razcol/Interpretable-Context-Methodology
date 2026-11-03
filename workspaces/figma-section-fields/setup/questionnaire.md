# Onboarding Questionnaire

Read this file when the user types `setup`. Ask ALL questions below in one pass, so the user can answer everything in one message. Replace the placeholders in the files listed, then scan the workspace for any `{{` left.

These questions configure the workspace. Per-run facts (Figma URL, repo for this run, folder name, target file for `element`) come with the trigger.

### Q1: Where are your section repos on this machine?
- Placeholders: `{{ORA_REPO}}`, `{{SMART_REPO}}`, `{{JAECOO_REPO}}`, `{{LUXURY_TRADE_REPO}}`, `{{OMODA_REPO}}`
- Files: `targets/repos.md`
- Type: free text, one path per repo (the repo root or its `code/` folder)
- Default: `/home/dev/ora-next`, `/home/dev/smart-next`, `/home/dev/jaecoo-next`, `/home/dev/colmobil-luxury-trade`, `/home/dev/omoda-next`

### Q2: Which repo should a run use when it does not name one?
- Placeholder: `{{DEFAULT_REPO}}`
- Files: `targets/repos.md`
- Type: selection: ora, smart, jaecoo, luxury-trade, omoda
- Default: ora

### Q3: Which file holds the Figma token?
- Placeholder: `{{FIGMA_ENV_FILE}}`
- Files: `shared/figma-cli-setup.md`, `shared/export-contract.md`
- Type: free text, an env file with a `FIGMA_ACCESS_TOKEN=` line
- Default: `/home/dev/cli/figma-cli/.env`

### Q4: Which local page should stage 05 open to see a section in the app?
- Placeholder: `{{ORA_TEST_ROUTE}}`
- Files: `targets/repos.md`
- Type: free text, a path on the dev server where your test page lists the sections you are building
- Default: `/model/ora-05-raz-test/`
- Derived: other repos start with "none yet". Stage 05 asks for a route the first time it runs on one of them and adds it to `targets/repos.md`.

---

## After Onboarding

Tell the user which values were written. Runs start with a trigger from `CLAUDE.md`, for example `new '<figma-url>' ora`.
