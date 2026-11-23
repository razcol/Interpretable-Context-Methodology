# Harness: Claude Code

Tool: `Agent`. Continue a running worker with `SendMessage`; a new `Agent` call starts fresh.

## Call shape

```text
subagent_type: general-purpose   # or Explore with --readonly
model: <from models.py>
effort: <from models.py>
description: <unit> (3-5 words)
prompt: <filled brief>
```

## Tiers and fallbacks

[tiers.json](tiers.json) is the single source of truth for the ranked top 3 `model` / `effort` pairs per slot (`light`, `mid`, `strong`, `strong/hardest`). Resolve all four slots once at run start:

```bash
python3 scripts/models.py table --harness claude-code
```

Walk a slot's ranked list in order only for **availability fallback** (call rejected). Use `--retry` for **quality escalation** (`light -> mid -> strong -> strong/hardest`). If none of the 3 in a slot is accepted, stop and report the unit.

This skill prescribes `effort`, which is what the harness requires before `effort` may be set. Keep `light` subagent prompts under 100K tokens (Haiku 5.5 jumps 5x in price above 100K).

## Never

- Turning on session `/fast` mode, leaving `model` unset, or using `low` effort in `mid` or `strong`.
- `fork` for a unit that needs a tier: a fork runs on the parent's model and ignores `model` and `effort`. Use it only when the parent's model is acceptable.

## Other agent types

- `Explore` (`models.py ... --readonly`) is read-only and reads excerpts. Fine for locating code at `light` or `mid`. Set `model` and `effort` on it as well.
- A custom `.claude/agents/*.md` may fix `model` in its frontmatter. Use one only if that model is in `tiers.json`.

## Parallel and background

Several `Agent` calls in one message run together. Workers run in the background and you are notified when each finishes; do not poll, and never report a result before the notice arrives. Keep a fan-out to about 5 workers per batch.
