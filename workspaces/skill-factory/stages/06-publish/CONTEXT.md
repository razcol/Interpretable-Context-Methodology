# Stage 06: Publish

Move the approved skill to its final home and record it in the index.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../05-approval-and-refine/output/approved-skill/` | Full folder | The skill to publish |
| Shared | `../../shared/preferences.md` | "Default Publish Destination" | The user's standing preference, if any |
| Shared | `../../shared/retention.md` | Full file | What to clear once this skill is published |
| User | (conversation) | Destination preference, if not already specified | Where the skill should live |

## Process

1. Check `shared/preferences.md` for a standing default. If it says "always ask", or no clear destination is specified there, ask: bundle into a specific workspace's `skills/` folder, or place in shared `_core/skills/` (for skills used by more than one workspace).
2. Move the approved skill folder to that destination.
3. Add or update its row in `shared/skill-index.md` (name, location, purpose, status).
4. Per `shared/retention.md`, clear this skill's `stages/01-intake/output/` through `stages/05-approval-and-refine/output/` contents (and the `04-draft-and-test` test log, if not already cleared). Confirm with the user before deleting if any output folder holds content unrelated to this run.

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Published skill | `_core/skills/[name]/` or `workspaces/[workspace]/skills/[name]/` | SKILL.md + supporting scripts |
| Updated index | `../../shared/skill-index.md` | Row added/updated for the published skill |
