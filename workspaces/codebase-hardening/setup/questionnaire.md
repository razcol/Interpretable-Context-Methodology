# Onboarding Questionnaire: Codebase Hardening

Read this file when the user types `setup`. Ask all questions below in a single conversational pass. The user should be able to answer everything in one message. Collect answers, replace placeholders across the listed files, then scan the workspace (except this file) for any remaining `{{` patterns.

Per-run details are not asked here. The target repo path and app root are collected at the start of each run by `stages/01-recon/CONTEXT.md`.

---

### Q1: Which stack will you harden most often?
- Placeholder: `{{PRIMARY_STACK}}`
- Files: `shared/preferences.md`
- Type: selection
- Options: "nextjs" (the only playbook shipped today)
- Default: "nextjs"

### Q2: Who approves which conventions become rules?
- Placeholder: `{{RATIFIER_NAME}}`
- Files: `shared/preferences.md`
- Type: free text
- Default: "The person running the workspace". Notes from other reviewers are pasted into the conversation at the approval step.

### Q3: What prefix should hardening branches use in the target repo?
- Placeholder: `{{BRANCH_PREFIX}}`
- Files: `shared/preferences.md`
- Type: free text
- Default: "harden/"

### Q4: What command should run all the checks in a target repo?
- Placeholder: `{{CHECK_COMMAND}}`
- Files: `shared/preferences.md`
- Type: free text
- Default: "npm run check". Use the package manager's own form for projects that use yarn or pnpm, for example "pnpm run check".

### Q5: Which optional dev tools may be added to a target repo as pinned dev dependencies?
- Placeholder: `{{ALLOWED_DEV_TOOLS}}`
- Files: `shared/preferences.md`
- Type: multiple choice, any combination, or "none"
- Options: "dependency-cruiser", "eslint-plugin-boundaries", "@ast-grep/cli", "none"
- Default: "dependency-cruiser, eslint-plugin-boundaries, @ast-grep/cli". These are dev dependencies only and never change the application, its runtime dependencies, or its bundle. A rule that needs a tool you did not allow is reported as blocked, not installed.

---

## After Onboarding

Tell the user: "Setup complete. Codebase Hardening is ready. Start a run anytime by giving me the path to a repository, and I will begin at `stages/01-recon/CONTEXT.md`. Before your first run, check `shared/prerequisites.md` to confirm Node.js and git are installed."

After all replacements, scan the entire workspace for remaining `{{` patterns, skipping this questionnaire, which lists them by design. If any remain, ask the user for the missing information before finishing setup.
