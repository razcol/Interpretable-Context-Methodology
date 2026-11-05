# Stage 02: Field Plan

Decide which ACF fields the section has, and write the click list you follow in WordPress. On `new` the run stops here until you say the group is saved. On `sync` the plan is compared with the group you already built.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-export/output/<node-id>/export-record.md` | Full file | Route, repo, folder |
| Profile | `../01-export/output/<node-id>/profile.json` | `fragments`, `breadcrumbs`, `appRoot`, `sectionsDir` | Shared fragments and page data |
| Scaffold | `../01-export/output/<node-id>/scaffold/<Folder>/Client<Folder>.js` | Props and defaults | The content pieces |
| Inspect | `../01-export/output/<node-id>/inspect.txt` | Hover lines | Hover-only content |
| Mobile preflight | `../01-export/output/<M>/inspect.txt`, `figma.png` | Only when the export record has `pair: <M>` (a node id) | Mobile crops and mobile-only content |
| Rules | `references/field-plan-rules.md` | Full file | What is and is not a field |
| Schema | `references/field-plan-schema.md` | Full file | `field-plan.json` shape |
| Report | `references/field-report-template.md` | Full file | Report layout and branches |
| Dashboard | `references/acf-dashboard-steps.md` | The block for the report's branch | Click steps |
| WP GraphQL | `../../../../_core/skills/wp-graphql/SKILL.md` | `patterns`, `section`, `diff-group` | Live schema |

## Process

1. Read the export record and the scaffold props. List the content pieces: headings, paragraphs, cards, pictures, buttons, links, disclaimer. When the record has `pair: <M>`, compare each piece with M's `figma.png` and `inspect.txt`.
2. Run `patterns` and `section <Folder> --refresh` with `--repo` set to the app root in the record.
3. Apply `references/field-plan-rules.md`. On `sync`, the live `tree` is the plan: copy it, then add only what the design has and the group lacks.
4. Write `output/<node-id>/field-plan.json` (schema in the reference) and `output/<node-id>/field-plan.md`: a table of field, ACF type, shape or clone source, repeater min and max, and why, then the questions the design raises, then the folder name.
5. On `sync`, run `diff-group <Folder> --plan output/<node-id>/field-plan.json`. `matches` true: go to step 7. Otherwise stop at the checkpoint with the differences.
6. On `new`, write `<app root>/<sectionsDir>/<Folder>/field-report.md` from the template, creating that folder. Do not add it to `.gitignore`. Stop at the checkpoint and end the run with: "The run ends here. Reply `continue <node-id>` after you save the group in WordPress."
7. Run the audit. On `sync`, load `../03-fragment/CONTEXT.md`.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 4 | The field plan table, the questions and the folder name | Change fields, answer the questions, confirm the name |
| 5 | `diff-group` differences on `sync` | Fix the group in WordPress, or change the plan |
| 6 | The field report path on `new` | Build and save the group, then reply `continue <node-id>` |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Page data | No field is breadcrumbs, SEO, page title, order or spacing other than `...Layout` |
| Shapes | Every picture or button field names its shape and clone source from `patterns` |
| Plan file | `field-plan.json` passes `diff-group` validation (no `USAGE` error) |
| Report | The report's first step matches its branch in `references/field-report-template.md` |
| Report place | `field-report.md` is beside the component, not in this stage's `output/` |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Field plan | `output/<node-id>/field-plan.md`, `field-plan.json` | Table and JSON |
| Field report (`new`) | `<app root>/<sectionsDir>/<Folder>/field-report.md` | `references/field-report-template.md` |
