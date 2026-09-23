# Stage 02: Draft Replies

Draft a reply in the user's own voice for every email flagged needs-reply, saved as a real Outlook draft.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../01-triage/output/triage-report.md` | Rows where needs-reply = `Yes` | The emails to draft replies for |
| Previous stage | `../01-triage/output/triage-report.md` | Rows where needs-reply = `Flag` | Ambiguous-age emails to surface to the user, not draft |
| Shared | `../../shared/tone-profile.md` | Full file | Voice reference for drafting |
| Skill | `../../skills/outlook-automation/SKILL.md` | Full file, then `reference/cli.md` as needed | outlookctl `draft` command (never `send`) |

## Process

1. Filter the triage report to needs-reply = `Yes` rows. Set aside needs-reply = `Flag` rows separately -- they are reported to the user, never drafted automatically.
2. Before drafting each `Yes` row, do a quick second look at its `Received` date against today's date (the triage run and the draft run are not always the same moment -- time may have passed, or the report may have been edited by the user). If a row that's about to be drafted now reads as clearly stale by the "Message Age / Staleness" guidance in `shared/priority-rubric.md`, do not draft it -- move it to the skipped list with a note, instead of drafting on stale triage data. This is a safety net, not a re-triage; only act if staleness is now obvious, otherwise trust the triage report's `Yes`. This row is now terminal (skipped, not drafted) -- carry its entry ID/store ID to step 7.
3. For each remaining row, compose a reply using the tone profile as the voice reference and any thread context already surfaced during triage.
4. Create the reply as an Outlook draft: `outlookctl draft --to "<recipient>" --subject "Re: <subject>" --body-text "<reply>" --reply-to-id <id> --reply-to-store <store>`. Never call `send` -- this workspace has no send step by design.
5. Record the created draft's entry ID, store ID, subject, and recipient. This row is now terminal (drafted) -- carry its entry ID/store ID to step 7.
6. Write the drafts-created list, including the `Flag` rows and any newly-skipped-for-staleness rows from step 2 as separate call-out sections (not silently dropped).
7. Mark as read every row that reached a terminal outcome in this run: every drafted row (step 4/5) and every newly-skipped-for-staleness row (step 2), via `outlookctl mark-read --id <id> --store <store>`. Do **not** mark `Flag` rows read yet -- they are not done until the checkpoint below resolves.
   - If a `mark-read` call fails, don't treat it as fatal -- note it explicitly in the drafts-created output (which row, which error) so it's visible rather than silently swallowed. A failed mark-read just leaves that row unread, which is the safe direction to fail in (it gets re-triaged next run instead of vanishing).
   - `mark-read` is idempotent -- safe to call even if the row was already marked read by an earlier partial run.
8. At the checkpoint below, the user may request an immediate draft for one or more `Flag` (or newly-skipped) rows. For each row the user asks to draft: create the draft as in step 4, record it as in step 5, then mark that row read too -- it's now terminal.
   For each `Flag` row the user does *not* ask to draft in this run: categorization/prioritization is already done (stage 01) and no draft is needed (the user just declined one), so both halves of "completely done" are satisfied -- mark it read. Record the resolution explicitly in the output (e.g. "surfaced at drafting checkpoint on `<date>`, no draft requested") so anyone reviewing Outlook later sees *why* an unreplied email was marked read, instead of it looking like something slipped through unactioned.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 7 | The list of created drafts (subject, recipient), plus a clearly separated list of `Flag` rows (ambiguous age, needs a human call) and any rows skipped in step 2 for having gone stale since triage | Whether any `Flag` or newly-skipped row should actually get a reply -- if so, the user says so explicitly and a draft is created for that row on request. Whatever the user decides here is final for this run: drafted rows and explicitly passed-on rows both get marked read in step 8, with the passed-on reasoning logged. |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Voice consistency | Each draft's greeting, sign-off, and formality match the tone profile's documented patterns |
| No auto-send | No `outlookctl send` call appears anywhere in this stage's execution |
| Full coverage | Every needs-reply = `Yes` row from the triage report has a corresponding created draft or an explicit skip reason in the output list |
| No silent drafting of ambiguous rows | No `Flag` row has a created draft unless the user explicitly requested one after seeing it called out |
| Mark-read completeness | Every row processed by this stage (drafted, skipped-for-staleness, or `Flag` resolved at the checkpoint -- drafted or declined) is marked read by the end of the run -- no row this stage touched is left unread once its outcome is final |
| Mark-read failure visibility | Any `mark-read` call that fails is named explicitly in the output (row + error), never silently dropped |
| Declined-flag reasoning | Every `Flag` row marked read without a draft has a one-line note recording when it was surfaced and that no draft was requested, not just a bare status change |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Drafts created | `output/drafts-created.md` | Markdown table of created drafts (subject, recipient, entry ID, store ID, source triage row), plus a "Flagged for Review" section (rows needing a human call on age -- each noted as drafted-on-request or declined-and-marked-read once the checkpoint resolves) and a "Skipped -- Went Stale" section (rows dropped by the step-2 safety net) |
| Outlook side effect | Drafts folder | One real draft per needs-reply email, unsent |
| Outlook side effect | Inbox | Drafted, staleness-skipped, and checkpoint-resolved `Flag` rows marked read via `outlookctl mark-read` |
