# Onboarding Questionnaire: Skill Factory

Read this file when the user types `setup`. Ask all questions below in a single conversational pass. The user should be able to answer everything in one message. Collect answers, replace placeholders across the listed files, then scan the workspace for any remaining `{{` patterns.

---

### Q1: When a skill is finished, where should it usually end up?
- Placeholder: `{{DEFAULT_PUBLISH_DESTINATION}}`
- Files: `shared/preferences.md`
- Type: selection
- Options: "Always ask me", "Default to `_core/skills/` (shared across workspaces)", "Default to a specific workspace's `skills/` folder (name it)"
- Default: "Always ask me"

### Q2: How thorough should research be before drafting a new skill?
- Placeholder: `{{RESEARCH_DEPTH}}`
- Files: `shared/preferences.md`
- Type: selection
- Options: "Quick -- go with the first solid approach found", "Thorough -- always compare at least two viable approaches before drafting"
- Default: "Thorough -- always compare at least two viable approaches before drafting"

---

## After Onboarding

Tell the user: "Setup complete. Skill Factory is ready. Start a new skill or maintain an existing one anytime -- just describe what you need, or name the skill you want to revisit. I'll begin at `stages/01-intake/CONTEXT.md`."

After all replacements, scan the entire workspace for remaining `{{` patterns. If any remain, ask the user for the missing information before finishing setup.
