# Stage 03: Fragment

Write the section's `.gql` from the group you built, after checking the group still matches the field plan.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-export/output/<node-id>/export-record.md` | Full file | Repo, folder |
| Profile | `../01-export/output/<node-id>/profile.json` | `fragments`, `appRoot`, `sectionsDir` | Spread names this repo uses |
| Stage 02 | `../02-field-plan/output/<node-id>/field-plan.json` | Full file | The approved plan |
| Rules | `references/fragment-rules.md` | Full file | How the tree becomes the selection |
| WP GraphQL | `../../../../_core/skills/wp-graphql/SKILL.md` | `section`, `diff-group`, `check-fragment` | Live checks |

## Process

1. Run `section <Folder> --refresh` with `--repo` set to the app root, then `diff-group <Folder> --plan <field-plan.json>`.
2. When `matches` is false, stop at the checkpoint with the differences. Do not write the fragment.
3. Write the selection from the live `tree`, following `references/fragment-rules.md`, with spread names from the profile.
4. Write `<app root>/<sectionsDir>/<Folder>/<Folder>.gql`. On `continue` the folder exists from stage 02. Create it when it does not.
5. Run `check-fragment` on that file. Fix every `missingOnSchema` and `shapeMismatches` entry. `deprecatedSelected` is fine. When `fragment.compared` is false, stop: the layout does not exist yet.
6. Run the audit. Write `output/<node-id>/fragment-record.md`.
7. Continue. Load `../04-conform-bind/CONTEXT.md`.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 2 | `diff-group` added, removed, typeChanged and cardinalityChanged lists | Fix the group in WordPress and reply `continue <node-id>`, or change the plan |
| 5 | `check-fragment` reports `compared` false | Save the layout in WordPress, then reply `continue <node-id>` |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Plan match | `diff-group` `matches` is true |
| Live names | Every top-level field in `tree` is selected under its saved name |
| Spreads | Media and buttons use the profile's shared fragments, never a hand-written `node { mediaItemUrl }` |
| Check | `check-fragment` has `compared` true, no `missingOnSchema` and no `shapeMismatches` |
| Name | `fragment <Folder> on <layoutType>` |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Fragment | `<app root>/<sectionsDir>/<Folder>/<Folder>.gql` | GraphQL fragment |
| Fragment record | `output/<node-id>/fragment-record.md` | `diff-group` and `check-fragment` summaries |
