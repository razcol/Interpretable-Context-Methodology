# Test Log Format

The shape of the trace produced every time `stages/04-draft-and-test` runs a skill against a real use case. This is an ephemeral, disposable artifact -- it exists to help the agent reason during the current run and to give the user visibility into what happened. It is not a long-term record and is not read by any other stage as a canonical source.

## Shape

```markdown
# Test Log: [skill-name]

## Use Case
[The real day-to-day scenario being tested, and its source: user-supplied or agent-suggested]

## Approach Under Test
[Which candidate approach, if more than one is being compared -- e.g. "CLI", "REST API"]

## Steps Taken
1. [What the agent did]
2. [What the agent did]
...

## Decisions Made
- [Decision] -- [reasoning]
- [Decision] -- [reasoning]

## Outcome
[What actually happened. Did it match the expected outcome? Where did it fall short, if anywhere?]

## Findings / Improvement Opportunities
[Anything noticed during the run that suggests a revision, even if the test technically passed]
```

## Rules

- One log per attempt. If testing two candidate approaches, produce two logs, then a short comparison note.
- Be concrete about outcomes. "Seemed to work" is not sufficient -- state what output was produced and how it was checked against the expected result.
- Findings should feed directly back into revising the draft in the same stage, not get deferred.
