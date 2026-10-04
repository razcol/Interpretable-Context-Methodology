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
└── shared/            (priority rubric, category map, tone profile, email lookup guide)
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
| Find a specific email or value (ID, link, name) in the mailbox | `shared/email-lookup-guide.md` |

## What to Load

| Task | Load These | Do NOT Load |
|------|-----------|-------------|
| Triage | `stages/01-triage/CONTEXT.md`, `shared/priority-rubric.md`, `shared/category-map.md`, `skills/outlook-automation/SKILL.md` | `shared/tone-profile.md`, `stages/02-draft-replies/` |
| Draft replies | `stages/02-draft-replies/CONTEXT.md`, `shared/tone-profile.md`, `stages/01-triage/output/triage-report.md`, `skills/outlook-automation/SKILL.md` | `shared/priority-rubric.md`, `shared/category-map.md` |
| Tone profile setup | `tone-profile/CONTEXT.md`, `skills/outlook-automation/SKILL.md` | `stages/01-triage/`, `stages/02-draft-replies/` |
| Ad-hoc email lookup | `shared/email-lookup-guide.md`, `skills/outlook-automation/SKILL.md` | `stages/`, `shared/tone-profile.md` |

## Stage Handoffs

Each stage writes its output to its own `output/` folder. The next stage reads from there for the **decisions** in it (needs-reply values, category choices, your edits and overrides). It never treats the email **facts** in it (existence, location, read state, categories, dates, IDs, thread contents) as current. See "Source of Truth" below. If you edit an output file, the next stage picks up your edited decisions.

## Source of Truth: Live Outlook Only

The live Outlook mailbox is the only source of truth for email data. You edit mail by hand at any time (read/unread, categories, moving, deleting, replying, drafts), so anything this workspace saved earlier may be out of date.

1. **Fresh ingest every run.** `process my inbox` always starts from a live `list --unread-only` on the inbox. Never seed a run from a saved report, a prior run's row list, or "unchanged from last run" entries.
2. **Saved files are records, not inputs.** `triage-report.md`, `drafts-created.md`, and `category-map.md` describe what a past run did or decided. They are never evidence of what is in Outlook now. A report from an earlier run, or one with an unresolved checkpoint, is not resumed. Re-derive everything from live Outlook. Overwrite it, do not reuse its rows or IDs.
3. **Re-verify before acting.** Immediately before any side effect (apply category, create draft, mark read), re-fetch that message live and confirm it still exists, is still where expected, and still matches what the decision was based on. Entry IDs can change when you move a message, so a stale ID is a reason to stop and look up the message again, never to guess.
4. **Respect your manual changes.** If the live state differs from the saved record (different category, already read, moved, deleted, already replied to, a newer message in the thread), the live state wins. Do not silently overwrite your manual choices. Report the difference and skip or ask.
5. **Never state Outlook facts from memory or files.** Claims such as "the draft is in your Drafts" or "that email is unread" must come from a live check in the same turn.

`tone-profile/` is not part of the per-run pipeline. It runs once, ahead of time, and its output (`shared/tone-profile.md`) is read by every `02-draft-replies` run afterward like any other shared file.

## outlookctl Runs via a Windows Bridge From This Workspace

Every stage in this workspace shells out to `outlookctl`, which requires genuine Windows COM automation -- `pywin32` cannot run on Linux at all, and cannot be reached reliably from a WSL shell by pointing at a `\\wsl$\...`/`\\wsl.localhost\...` path either (that has been tested and found to intermittently fail even when it appears to work once). The reliable path is `skills/outlook-automation/outlookctl-bridge.sh`, which mirrors the tool to a native Windows path and runs it via `powershell.exe`. Always invoke `outlookctl` through that script, not directly. See `skills/outlook-automation/SKILL.md` for usage.
