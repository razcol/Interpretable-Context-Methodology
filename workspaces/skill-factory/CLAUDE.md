# Skill Factory

A production system for creating new agent skills and maintaining existing ones, validated through real day-to-day usage testing rather than guesswork.

## Folder Map

```
skill-factory/
├── CLAUDE.md               (you are here)
├── CONTEXT.md              (start here for task routing)
├── setup/
│   └── questionnaire.md    (one-time onboarding)
├── stages/
│   ├── 01-intake/          (request or existing skill name to scoped ticket)
│   ├── 02-clarify/         (scoped ticket to clarified requirements, new skills only)
│   ├── 03-research/        (requirements to candidate implementation approaches)
│   ├── 04-draft-and-test/  (candidates to a validated, tested skill draft)
│   ├── 05-approval-and-refine/  (tested draft to user-approved skill)
│   └── 06-publish/         (approved skill to its final home)
└── shared/
    ├── skill-index.md          (registry of every skill this workspace has built)
    ├── authoring-conventions.md (what a good SKILL.md looks like)
    ├── test-log-format.md      (shape of the ephemeral test trace used in stage 04)
    └── preferences.md          (default publish destination, research depth -- set during setup)
```

## Triggers

| Keyword | Action |
|---------|--------|
| `setup` | Run one-time onboarding -- configures publish preferences and defaults |
| `status` | Show pipeline completion for all six stages |

### How `status` works

Scan `stages/*/output/` folders. For each stage, if the output folder contains files (other than .gitkeep), the stage is COMPLETE. Otherwise PENDING. Render:

```
Pipeline Status: skill-factory

  [01-intake] --> [02-clarify] --> [03-research] --> [04-draft-and-test] --> [05-approval] --> [06-publish]
     STATUS          STATUS           STATUS               STATUS               STATUS           STATUS
```

## Routing

| Task | Go To |
|------|-------|
| Scope a new skill request, or locate an existing skill | `stages/01-intake/CONTEXT.md` |
| Pin down exact requirements for a new skill | `stages/02-clarify/CONTEXT.md` |
| Research implementation approaches | `stages/03-research/CONTEXT.md` |
| Draft and test a skill against real usage | `stages/04-draft-and-test/CONTEXT.md` |
| Get user approval, revise if needed | `stages/05-approval-and-refine/CONTEXT.md` |
| Publish the finished skill | `stages/06-publish/CONTEXT.md` |

## What to Load

| Task | Load These | Do NOT Load |
|------|-----------|-------------|
| Intake a request | `shared/skill-index.md` | Everything else -- intake is a routing decision only |
| Clarify requirements | `stages/01-intake/output/`, `stages/02-clarify/references/*` | `shared/authoring-conventions.md`, stages 03-06 |
| Research approaches | `stages/02-clarify/output/` (or `stages/01-intake/output/` for existing-mode approach changes), `shared/authoring-conventions.md`, `shared/preferences.md` | stages 01-02 references, stages 04-06 |
| Draft and test | `stages/03-research/output/` (or resolved skill folder for existing-mode), `shared/authoring-conventions.md`, `shared/test-log-format.md` | stages 01-03 references, stages 05-06 |
| Approve and refine | `stages/04-draft-and-test/output/` | Everything upstream of stage 04 |
| Publish | `stages/05-approval-and-refine/output/`, `shared/skill-index.md`, `shared/preferences.md` | Everything upstream of stage 05 |

## Stage Handoffs

Each stage writes its output to its own `output/` folder. The next stage reads from there. If you edit an output file between stages, the next stage picks up your edits.

New-skill requests flow 01 through 06 in sequence. Existing-skill maintenance requests skip 02-clarify (always) and usually skip 03-research, entering directly at 04-draft-and-test with the current skill folder as input.
