# Stage 01: Intake

Scope the request and determine whether this is a new skill or maintenance of an existing one.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| User | (conversation) | Skill request or existing skill name | The task to scope |
| Shared | `../../shared/skill-index.md` | Full file | Fast lookup for existing-mode |

## Process

1. Ask the user whether this is a new skill request or maintenance of an existing skill.
2. If new: capture the raw request and derive a skill slug (lowercase-with-hyphens).
3. If existing: look up the name in `shared/skill-index.md` first. The index can go stale, so if not found there, search outside this workspace's own folder: check every `_core/skills/*/SKILL.md` and every `workspaces/*/skills/*/SKILL.md` across the whole repo (not just skill-factory's own `shared/` or any single workspace) for a matching name or slug. Match against the `name:` frontmatter and folder slug inside each `SKILL.md`, not a literal filename search for the request text -- a skill folder is rarely named exactly what the user typed.
4. If multiple matches are found, ask the user to disambiguate.
5. Write the intake note.

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Intake note | `output/intake-note.md` | Skill slug, raw request, mode (new/existing), resolved skill folder path if existing |
