# Onboarding Questionnaire

Read this file when the user types `setup`. Ask ALL questions below in a single conversational pass. The user should be able to answer everything in one message. Collect answers. Replace placeholders across the specified files.

These questions configure the workspace. They are not a run. Per-run facts (Figma file or URL, node id, export path, render location) are asked by stage 01 and stage 03, not here.

### Q1: Where is the Jaecoo repo on this machine?
- Placeholder: `{{JAECOO_REPO}}`
- Files: `targets/repos.md`
- Type: free text
- Default: `/home/dev/jaecoo-next/code`

### Q2: Where is the luxury trade repo on this machine?
- Placeholder: `{{LUXURY_TRADE_REPO}}`
- Files: `targets/repos.md`
- Type: free text
- Default: `/home/dev/colmobil-luxury-trade/code`

### Q3: Which project should a run use when it does not name one?
- Placeholder: `{{DEFAULT_TARGET}}`
- Files: `targets/repos.md`
- Type: selection
- Options: jaecoo, luxury-trade
- Default: jaecoo

### Q4: What is the sections directory, relative to the repo?
- Placeholder: `{{SECTIONS_DIR}}`
- Files: `targets/repos.md`
- Type: free text
- Default: `app/components/Sections`

WordPress fields are added by hand in that site's dashboard, from `<export-dir>/<Folder>/field-report.md`.

---

## After Onboarding

Tell the user which paths were written into `targets/repos.md`. A run starts at `stages/01-figma-export/CONTEXT.md`.

After all replacements, scan the entire workspace for remaining `{{` patterns. If any remain, ask for the missing info.
