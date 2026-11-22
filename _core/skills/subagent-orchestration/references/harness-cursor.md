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

Each slot is a ranked list of three slugs, best fit first: the primary, then fallback 1 and fallback 2.

| Slot | Primary | Fallback 1 | Fallback 2 |
|------|---------|------------|------------|
| mid (Claude, default) | `claude-sonnet-5-5-high` | `gpt-5.6-sol-medium` | `gemini-4-neon-medium` |
| mid (Grok) | `grok-4.7-medium` | `grok-4.7-high` | `claude-sonnet-5-5-high` |
| strong (Claude, default) | `claude-opus-5-5-medium` | `claude-opus-5-5-high` | `grok-4.7-high` |
| strong hardest units and strong retries (Claude) | `claude-opus-5-5-high` | `grok-4.7-high` | `gpt-5.6-sol-medium` |
| strong (Grok) | `grok-4.7-high` | `claude-opus-5-5-high` | `gpt-5.6-sol-medium` |
| strong hardest and strong retries (Grok) | `claude-opus-5-5-high` (Grok has no step above `grok-4.7-high`) | `grok-4.7-high` | `gpt-5.6-sol-medium` |

Pick the family the user or the workspace's unit table names; Claude when none is named. Use the primary. When the IDE has not enabled it or the call rejects it, use fallback 1, then fallback 2, in that order. When the IDE's enabled models are known, `models.py pick ... --available <slug,slug,...>` makes that choice for you. If none of the three is accepted, stop and report the unit; do not pick a slug outside its row.

All of these slugs were listed by `cursor-agent models` on 2026-11-22. The IDE enabled `claude-sonnet-5-5-high`, `claude-opus-5-5-high`, `grok-4.7-high`, `gpt-5.6-sol-medium`, `gemini-4-neon-medium` and `gemini-4-carbon-medium` that day, so strong (Claude) resolved to fallback 1, `claude-opus-5-5-high`.

## Never

`fast`, `auto`, `inherit`, any slug ending in `-fast` (Claude, Grok, GPT and Composer all have them), any `-low`, `-none` or `-minimal` slug, `composer-*`, `grok-4.7-low`, `grok-4.7-xhigh`, every `cursor-grok-*` (4.5 and 4.6), and any slug not in the table above. A `Task` call without `model` is a failed check: respawn the unit with `model` before going on.

## Subagent types

`generalPurpose` for any unit that writes files. `explore` is read-only. Set `model` on both.

## Checking the slugs

`cursor-agent models` lists what is current. `scripts/models.py check --harness cursor` compares every primary and fallback in `tiers.json` with that list and with the never list. When `cursor-agent models` fails or lists nothing (offline or sandboxed, for example `getaddrinfo EAI_AGAIN`), the check prints `SKIP: cursor-agent models unavailable (<reason>)` and exits 0. That means the slugs were not verified, not that they failed. Run it with network access to verify them.
