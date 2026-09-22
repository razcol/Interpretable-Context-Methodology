# Skill Factory

Create new agent skills and maintain existing ones through a six-stage process grounded in real-usage testing.

## Task Routing

| Task Type | Go To | Description |
|-----------|-------|-------------|
| New skill request, or name an existing skill for maintenance | `stages/01-intake/CONTEXT.md` | Scopes the request and determines new vs. existing mode |
| Pin down exact requirements | `stages/02-clarify/CONTEXT.md` | Targeted questions to remove ambiguity (new skills only) |
| Explore implementation approaches | `stages/03-research/CONTEXT.md` | CLI vs REST API vs library vs browser automation, with tradeoffs |
| Draft and test against real usage | `stages/04-draft-and-test/CONTEXT.md` | Builds draft(s), tests against a real day-to-day case, selects the winner |
| Get approval, revise if needed | `stages/05-approval-and-refine/CONTEXT.md` | User reviews the tested draft and approves or sends it back |
| Publish the finished skill | `stages/06-publish/CONTEXT.md` | Moves the skill to `_core/skills/` or a workspace's `skills/` folder |

## Shared Resources

| Resource | Location | Contains |
|----------|----------|----------|
| Skill index | `shared/skill-index.md` | Registry of every skill built: name, location, purpose, status |
| Authoring conventions | `shared/authoring-conventions.md` | What a good SKILL.md looks like (frontmatter, progressive disclosure, when to add scripts) |
| Test log format | `shared/test-log-format.md` | Consistent shape for the ephemeral test trace produced in stage 04 |
| Preferences | `shared/preferences.md` | Default publish destination and research depth, set once during setup |
| Retention | `shared/retention.md` | How long stage outputs and the test log should stick around, and when to clear them |
