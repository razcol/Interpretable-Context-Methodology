# Codebase Hardening

Studies a project's real conventions and turns the ones you approve into checks that agent-written code cannot bypass, without breaking what already exists.

## Folder Map

```
codebase-hardening/
├── CLAUDE.md          (you are here)
├── CONTEXT.md         (start here for task routing)
├── setup/             (one-time onboarding questionnaire)
├── scripts/           (measure and validate tools, Node, no dependencies)
├── playbooks/         (stack knowledge: core probes, Next.js recon, enforcement, implementation)
├── shared/            (schemas, policies, dispatch notes, preferences)
└── stages/
    ├── 01-recon/              (target repo to project profile)
    ├── 02-measure/            (profile to small validated probe reports)
    ├── 03-synthesize/         (reports to ratified convention candidates)
    ├── 04-enforcement-design/ (rules to mechanisms, READY or DEFERRED)
    ├── 05-implement/          (READY rules to a hardened branch)
    ├── 06-verify/             (fresh-context attempt to break the gates)
    └── 07-handoff/            (agent guide and follow-up plan)
```

## Triggers

| Keyword | Action |
|---------|--------|
| `setup` | Run onboarding. Reads `setup/questionnaire.md` |
| `status` | Show pipeline completion for all seven stages |
| `followup <rule-id>` | Start a follow-up pass for one deferred rule the user has cleaned up. Go to `stages/04-enforcement-design/CONTEXT.md` |

### How `status` works

Scan `stages/*/output/`. A stage with files other than .gitkeep is COMPLETE, otherwise PENDING. Render:

```
Pipeline Status: codebase-hardening

  [01-recon] -> [02-measure] -> [03-synthesize] -> [04-enforcement] -> [05-implement] -> [06-verify] -> [07-handoff]
     STATUS        STATUS          STATUS             STATUS              STATUS           STATUS         STATUS
```

## Routing

| Task | Go To |
|------|-------|
| Start on a new target repo | `stages/01-recon/CONTEXT.md` |
| Run the probes | `stages/02-measure/CONTEXT.md` |
| Decide which conventions become rules | `stages/03-synthesize/CONTEXT.md` |
| Design enforcement and sort READY from DEFERRED | `stages/04-enforcement-design/CONTEXT.md` |
| Build the gates | `stages/05-implement/CONTEXT.md` |
| Try to break the gates | `stages/06-verify/CONTEXT.md` |
| Produce the agent guide and follow-up plan | `stages/07-handoff/CONTEXT.md` |

## What to Load

| Task | Load These | Do NOT Load |
|------|-----------|-------------|
| Recon | Stage 01 files, `shared/preferences.md`, the recon file of the chosen playbook | Everything in stages 02 to 07 |
| Measure | Stage 02 files, the profile, `shared/probe-report-schema.md`, one probe at a time | Other reports, source files beyond drill-down |
| Synthesize | Stage 03 files, the reports | Evidence files, source files, playbook enforcement files |
| Enforcement design | Stage 04 files, ratified candidates, ladder, deferral policy, tamper protection | Probe reports, evidence |
| Implement | Stage 05 files, the enforcement plan, implementation rules | Candidates, reports, deferred-rules details |
| Verify | Stage 06 files, the change log, the bypass list | Everything from stages 01 to 04. Fresh context only |
| Handoff | Stage 07 files, verification report, plan, deferred rules | Probe reports, candidates |

## Stage Handoffs

Each stage writes to its own `output/`. The next stage reads from there. If you edit an output file between stages, the next stage picks up your edits. Stage 05 also writes to the target repo, on a new branch, in a separate worktree.

## Ground Rules

- Scripts measure. Agents interpret. Never count or list files by reading them.
- Only Stage 05 writes to the target repo, and never to application code.
- A rule with existing violations is DEFERRED by default. Never enforce it to be helpful.
