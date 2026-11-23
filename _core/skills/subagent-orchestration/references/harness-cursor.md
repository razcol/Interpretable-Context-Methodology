# Harness: Cursor

Tool: `Task`. Arguments: `subagent_type`, `model`, `description`, `prompt`, plus `readonly`, `run_in_background`, `resume`.

## Call shape

```text
subagent_type: generalPurpose   # or explore with --readonly
model: <from models.py>
description: <unit>
prompt: <filled brief>
```

Effort is part of the slug. There is no separate effort field.

## Tiers and fallbacks

[tiers.json](tiers.json) is the single source of truth for the ranked top 3 per slot (`light`, `mid`, `strong`, `strong/hardest`). Resolve all four slots once at run start against the IDE's enabled models:

```bash
python3 scripts/models.py table --harness cursor --available <enabled,slugs>
```

Walk a slot's ranked list in order only for **availability fallback** (primary not enabled or rejected). Use `--retry` for **quality escalation** (`light -> mid -> strong -> strong/hardest`). If none of the 3 in a slot is accepted, stop and report the unit; do not pick a slug outside its slot.

## Never

`fast`, `auto`, `inherit`, any slug ending in `-fast` (2x–6x cost/pool burn for the same intelligence), any `-none` or `-minimal` slug, `grok-4.7-low`, `grok-4.7-xhigh`, every `cursor-grok-*`, and any slug not in the slot's ranked list. A `Task` call without `model` is a failed check: respawn the unit with `model` before going on.

## Subagent types

`generalPurpose` for any unit that writes files. `explore` (`models.py ... --readonly`) for read-only lookups. Set `model` on both.

## Checking the slugs

`cursor-agent models` lists what is current. `scripts/models.py check --harness cursor` validates every primary and fallback in `tiers.json` against the ban rules, verifies that every escalation step strictly changes the primary, and checks each slug against `cursor-agent models`. When `cursor-agent models` fails or lists nothing (offline or sandboxed, for example `getaddrinfo EAI_AGAIN`), the check prints `SKIP: cursor-agent models unavailable (<reason>)` and exits 0 (not verified, not failed).
