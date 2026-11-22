# Harness: Claude Code

Tool: `Agent`. Continue a running worker with `SendMessage`; a new `Agent` call starts fresh.

## Call shape

```text
subagent_type: general-purpose
model: sonnet            # mid
effort: high
description: <unit> (3-5 words)
prompt: <filled brief>
```

Each slot is a ranked list of three `model` / `effort` pairs, best fit first: the primary, then fallback 1 and fallback 2.

| Slot | Primary | Fallback 1 | Fallback 2 |
|------|---------|------------|------------|
| mid | `sonnet` / `high` | `opus` / `medium` | `opus` / `high` |
| strong | `opus` / `high` | `opus` / `xhigh` | `sonnet` / `high` |
| strong hardest units and strong retries | `opus` / `xhigh` | `opus` / `high` | `opus` / `max` |

Use the primary. When the call rejects it, use fallback 1, then fallback 2, in that order. If none of the three is accepted, stop and report the unit. `models.py pick --harness claude-code ...` prints the primary and the ordered `fallbacks`.

This skill prescribes `effort`, which is what the harness requires before `effort` may be set.

## Never

- `haiku` (below mid), effort `low`, leaving `model` unset, turning on the session `/fast` mode.
- `fork` for a unit that needs a tier: a fork runs on the parent's model and ignores `model` and `effort`. Use it only when the parent's model is acceptable.
- No Grok: the `Agent` tool takes Claude models only. A rejected `sonnet` goes up to `opus` (the mid row's fallbacks).

## Other agent types

- `Explore` is read-only and reads excerpts. Fine for locating code at mid. Set `model` on it as well.
- A custom `.claude/agents/*.md` may fix `model` in its frontmatter. Use one only if that model is in the table.

## Parallel and background

Several `Agent` calls in one message run together. Workers run in the background and you are notified when each finishes; do not poll, and never report a result before the notice arrives. Keep a fan-out to about 5 workers per batch.
