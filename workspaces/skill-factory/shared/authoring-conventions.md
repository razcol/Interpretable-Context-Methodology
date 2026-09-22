# SKILL.md Authoring Conventions

What a good skill looks like in this system. Used during research (to know what's buildable) and drafting (to know how to write it). Based on Anthropic's Agent Skills format ([announcement](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), [best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)).

## Structure

A skill is a folder containing a `SKILL.md` file, and optionally supporting scripts or resources:

```
skill-name/
├── SKILL.md       (required entry point)
├── scripts/       (optional -- executable helpers the skill can invoke)
└── references/    (optional -- longer docs the skill points to, loaded only when needed)
```

## SKILL.md Frontmatter

Every SKILL.md starts with YAML frontmatter containing at minimum:

```yaml
---
name: skill-name
description: One or two sentences describing what this skill does and when to use it.
---
```

The `name` and `description` are pre-loaded into the agent's context at startup for every installed skill, before the rest of the file is read. Keep the description specific enough that an agent can tell when the skill applies, without reading the body.

## Progressive Disclosure

The agent reads the SKILL.md body only when the skill becomes relevant to the current task, and reads any linked reference files only if the task needs that level of detail. This means:

- Keep SKILL.md itself concise. Every token in it competes with conversation history once loaded.
- Move long, situational detail (edge cases, less-common options, deep API references) into separate files under `references/` and link to them, rather than inlining everything.
- Scripts that do real work (parsing, calling an API, transforming files) belong in `scripts/`, invoked by the agent, not reimplemented as prose instructions.

## When to Add Scripts vs. Inline Instructions

- If a step is deterministic and mechanical (parse this file format, call this endpoint with these parameters), write a script. Scripts are more reliable than an agent re-deriving the same logic every run.
- If a step requires judgment (deciding what content to write, how to phrase something, which of several valid options fits the situation), leave it as instructions for the agent to reason through.

## Quality Bar Before Publishing

A skill is ready to publish only when it has been tested against a real day-to-day use case (see `test-log-format.md`) and produced the expected outcome, not just a plausible-looking one.
