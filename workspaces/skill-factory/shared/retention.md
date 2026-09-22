# Artifact Retention

How long pipeline artifacts in this workspace should stick around, and when it's safe to clear them.

## Stage Outputs (`stages/*/output/`)

Each stage's output is an input to the next stage, so keep it until the skill it belongs to reaches **Stage 06: Publish**.

Once a skill is published:
- The published skill folder (`_core/skills/[name]/` or `workspaces/[workspace]/skills/[name]/`) and its row in `shared/skill-index.md` become the permanent record.
- The stage outputs that fed that skill through `01-intake` -> `05-approval-and-refine` are no longer needed and can be cleared.

For existing-skill maintenance runs (which skip `02-clarify` and usually `03-research`), the same rule applies to whichever stage outputs were produced.

## Test Run Log (`stages/04-draft-and-test/output/test-log.md`)

Explicitly ephemeral and disposable (see `shared/test-log-format.md`). It's not read by any later stage as a canonical source.

- Safe to delete as soon as the findings it surfaced have been folded into the draft/skill and the run is done -- there is no need to wait for publish.
- If it contains findings worth preserving long-term (e.g. a quirk that will recur), copy those into the skill's own `LOG.md` or `SKILL.md` rather than keeping the test log itself around.

## What Never Gets Cleared

- `shared/skill-index.md` -- permanent registry of every skill built.
- `shared/preferences.md`, `shared/authoring-conventions.md`, `shared/test-log-format.md` -- standing configuration, not per-run artifacts.
- Published skill folders themselves.

## Applying This

This workspace does not run automated cleanup. Treat this file as the rule to follow manually (or delegate to the agent) after a skill completes Stage 06 -- clear that skill's `stages/*/output/` contents once the publish step confirms the skill is live at its destination.
