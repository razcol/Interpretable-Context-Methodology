# Harness: Cursor

Tool: `Task`. Arguments: `subagent_type`, `model`, `description`, `prompt`, plus `readonly`, `run_in_background`, `resume`.

## Call shape

```text
subagent_type: generalPurpose
model: claude-sonnet-5-5-high
description: <unit>
prompt: <filled brief>
```

Effort is part of the slug. There is no separate effort field.

| Tier | Claude (default) | Grok |
|------|------------------|------|
| mid | `claude-sonnet-5-5-high` | `grok-4.7-medium` |
| strong | `claude-opus-5-5-medium` | `grok-4.7-high` |
| strong, hardest units and strong retries | `claude-opus-5-5-high` | `claude-opus-5-5-high` (Grok has no step above `grok-4.7-high`) |

Pick the family the user or the workspace's unit table names; Claude when none is named. When a slug is rejected, use the other family's slug in the same tier, then the next tier up.

## Never

`fast`, `auto`, `inherit`, any slug ending in `-fast` (Claude, Grok, GPT and Composer all have them), `composer-*`, `grok-4.7-low`, `grok-4.7-xhigh`, every `cursor-grok-*` (4.5 and 4.6), and any slug not in the table above. A `Task` call without `model` is a failed check: respawn the unit with `model` before going on.

## Subagent types

`generalPurpose` for any unit that writes files. `explore` is read-only. Set `model` on both.

## Checking the slugs

`cursor-agent models` lists what is current. `scripts/models.py check --harness cursor` compares it with `tiers.json`.
