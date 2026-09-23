# Outlook Email Manager

Triages unread Outlook Classic email (categorize, label, prioritize) and drafts replies in your own voice for every email that still needs one. Triage weighs each email's age: clearly stale emails are skipped (no draft), and emails with ambiguous age are flagged for you to decide rather than drafted automatically. Each email is marked read only once the pipeline is fully done with it (category applied and, if it needed a reply, drafted or explicitly resolved) so it won't be re-ingested on the next run.

## Folder Map

```
outlook-email-manager/
├── CLAUDE.md          (you are here)
├── CONTEXT.md         (start here for task routing)
├── setup/             (onboarding questionnaire)
├── skills/            (bundled outlookctl CLI + Claude skill, with a local category patch)
├── tone-profile/      (one-time voice setup, run before first real pipeline run)
├── stages/
│   ├── 01-triage/     (unread inbox to prioritized, categorized report)
│   └── 02-draft-replies/  (needs-reply emails to real Outlook drafts)
└── shared/            (priority rubric, category map, tone profile)
```

## Triggers

| Keyword | Action |
|---------|--------|
| `setup` | Run onboarding questionnaire |
| `status` | Show pipeline completion for all stages |
| `process my inbox` | Run the full pipeline once: 01-triage then 02-draft-replies |
| `learn my tone` | Run the one-time tone-profile setup (see `tone-profile/CONTEXT.md`) |

## Routing

| Task | Go To |
|------|-------|
| Triage unread email | `stages/01-triage/CONTEXT.md` |
| Draft replies for flagged email | `stages/02-draft-replies/CONTEXT.md` |
| Learn or refresh voice/tone | `tone-profile/CONTEXT.md` |

## What to Load

| Task | Load These | Do NOT Load |
|------|-----------|-------------|
| Triage | `stages/01-triage/CONTEXT.md`, `shared/priority-rubric.md`, `shared/category-map.md`, `skills/outlook-automation/SKILL.md` | `shared/tone-profile.md`, `stages/02-draft-replies/` |
| Draft replies | `stages/02-draft-replies/CONTEXT.md`, `shared/tone-profile.md`, `stages/01-triage/output/triage-report.md`, `skills/outlook-automation/SKILL.md` | `shared/priority-rubric.md`, `shared/category-map.md` |
| Tone profile setup | `tone-profile/CONTEXT.md`, `skills/outlook-automation/SKILL.md` | `stages/01-triage/`, `stages/02-draft-replies/` |

## Stage Handoffs

Each stage writes its output to its own `output/` folder. The next stage reads from there. If you edit an output file, the next stage picks up your edits.

`tone-profile/` is not part of the per-run pipeline. It runs once, ahead of time, and its output (`shared/tone-profile.md`) is read by every `02-draft-replies` run afterward like any other shared file.

## outlookctl Runs via a Windows Bridge From This Workspace

Every stage in this workspace shells out to `outlookctl`, which requires genuine Windows COM automation -- `pywin32` cannot run on Linux at all, and cannot be reached reliably from a WSL shell by pointing at a `\\wsl$\...`/`\\wsl.localhost\...` path either (that has been tested and found to intermittently fail even when it appears to work once). The reliable path is `skills/outlook-automation/outlookctl-bridge.sh`, which mirrors the tool to a native Windows path and runs it via `powershell.exe`. Always invoke `outlookctl` through that script, not directly. See `skills/outlook-automation/SKILL.md` for usage.
