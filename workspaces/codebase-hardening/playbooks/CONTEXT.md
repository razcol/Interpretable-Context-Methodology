# Playbooks

Stack knowledge, kept apart from the stages so the stages never change when a stack is added.

## What Loads

Always load the `core` row. Also load the row that matches the Primary Stack in `../shared/preferences.md`. Never load another stack's row.

| Playbook | Recon | Probes | Enforcement | Implementation |
|----------|-------|--------|-------------|----------------|
| core | none | `core/probes/` | none | none |
| nextjs | `nextjs/recon.md` | `nextjs/probes/` | `nextjs/enforcement.md` | `nextjs/implementation.md` |

## Status

| Playbook | Validation state |
|----------|------------------|
| core | Generic. Its abstractions count as proven only after a second stack uses them. |
| nextjs | Probes ran against one Next.js 14 JavaScript project (App Router). Enforcement and implementation recipes are written from documentation and have not been run yet. Verify each recipe against the installed tool versions. |

## Adding a Stack

1. Create `playbooks/<stack>/` with `recon.md`, `enforcement.md`, `implementation.md`, and `probes/`.
2. Add a row to the table above.
3. Add the stack name to the question about the primary stack in `setup/questionnaire.md`.
4. Write stack probes as files with a `json measure` block. See `../shared/scripts-reference.md`.

No stage file needs to change.
