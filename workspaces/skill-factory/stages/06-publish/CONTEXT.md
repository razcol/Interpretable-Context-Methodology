# Stage 06: Publish

Move the approved skill to its final home and record it in the index.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../05-approval-and-refine/output/approved-skill/` | Full folder | The skill to publish |
| Shared | `../../shared/preferences.md` | "Default Publish Destination" | The user's standing preference, if any |
| User | (conversation) | Destination preference, if not already specified | Where the skill should live |

## Process

1. Check `shared/preferences.md` for a standing default. If it says "always ask", or no clear destination is specified there, ask: bundle into a specific workspace's `skills/` folder, or place in shared `_core/skills/` (for skills used by more than one workspace).
2. Move the approved skill folder to that destination.
3. Add or update its row in `shared/skill-index.md` (name, location, purpose, status).

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Published skill | `_core/skills/[name]/` or `workspaces/[workspace]/skills/[name]/` | SKILL.md + supporting scripts |
| Updated index | `../../shared/skill-index.md` | Row added/updated for the published skill |
