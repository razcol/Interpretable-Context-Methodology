# Stage 01: Triage

Categorize, label, and prioritize every unread email in the inbox.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Outlook (via outlookctl) | Inbox, unread items | All unread emails | The work item set for this run |
| Outlook (via outlookctl) | Relevant threads | Prior messages in-thread, fetched only when needed | Context for categorization/prioritization |
| Outlook (via outlookctl) | `category list` | Full list | Ground truth to match against before suggesting new categories |
| Shared | `../../shared/priority-rubric.md` | Full file | Scoring signals, weights, VIP sender list |
| Shared | `../../shared/category-map.md` | Full file | Previously approved category matches, for consistency run over run |
| Skill | `../../skills/outlook-automation/SKILL.md` | Full file, then `reference/cli.md` as needed | outlookctl commands: `list`, `search`, `get`, `category list/get/set` |

## Source of Truth

Live Outlook is the only source of email data (see "Source of Truth: Live Outlook Only" in `../../CLAUDE.md`). Specific rules for this stage:

- Do not read the existing `output/triage-report.md` to get rows, IDs, categories, or needs-reply values. It is a record of a previous run and is overwritten by this one. If it shows an unresolved checkpoint, do not resume it. Triage from the live unread list.
- `shared/category-map.md` holds mapping decisions only. Read each message's current categories live from `list`/`category get`.
- Never write "unchanged from prior run" for an ID or any email field. Every row's data comes from this run's live fetch.

## Process

1. List unread emails live: `outlookctl list --folder inbox --unread-only`. This list, fetched now, defines the work set for this run. Record the fetch time in the report.
2. For each email, pull prior thread context via `outlookctl search`/`get` if the subject/sender indicates an ongoing conversation. Also check for a newer message in the thread, or a reply from the user in Sent Items, that supersedes the email.
3. Fetch the mailbox's defined categories: `outlookctl category list`. Match each email to an existing category where reasonable. If no good match exists, suggest a new category rather than inventing one silently -- flag it in the report for the user to confirm.
4. Update `shared/category-map.md` with any newly approved matches or suggestions from this run.
5. Score priority per `shared/priority-rubric.md`: urgency/deadline language, direct ask vs. FYI, sender importance/VIP list, active thread, time-sensitive content. Newsletters/automated/mass-distribution default low.
6. Check message age against today's date per the "Message Age / Staleness" section of `shared/priority-rubric.md`, and set needs-reply to one of three values:
   - `No` -- clearly stale (old, or tied to a passed date/event). Do not draft.
   - `Yes` -- clearly still worth a reply (recent, or an active thread).
   - `Flag` -- ambiguous age with no clear signal either way. Do not decide on the agent's behalf; this row gets surfaced to the user at the checkpoint below instead of being auto-drafted.
7. Apply the resolved category back onto the message: `outlookctl category set --id <id> --store <store> --categories "<name>"`. Read the message's live categories first. If it already has a category (yours, set by hand or by an earlier run) that matches the resolved one, do nothing. If it has a different one, do not overwrite it. Report the difference in the triage report and let the checkpoint decide. Only apply to messages with no category, or where you approve the change.
8. Write the triage report, including each email's entry ID and store ID (needed later for mark-read -- see step 9 and stage 02).
9. **After** the checkpoint below is resolved (category suggestions confirmed, any needs-reply flips applied) mark as read only the rows whose needs-reply is `No`: `outlookctl mark-read --id <id> --store <store>`. Triage is the last stage that will ever touch a `No` row, so this is where "completely done" happens for it.
   - **Re-verify each row live right before marking it read.** The checkpoint can sit open for a long time and you may have changed the mailbox in between. `get` the message by its entry ID and confirm it still exists, is still in the Inbox, and is still unread. If it was deleted or moved, or the ID no longer resolves, do not mark it and do not guess. Try one live lookup by subject, sender, and received date. If that finds exactly one match, use it. Otherwise report it under Notes. If it is already read, skip it as done. If its live category differs from the report, treat it as your manual change and leave it.
   - If the checkpoint is still unresolved when a new run starts, the old report is discarded and nothing is marked read on its authority. The new run re-triages from the live unread list.
   - Do **not** mark `Yes` or `Flag` rows as read here -- they still have work pending in stage 02 (drafting, or being surfaced for a human decision). Marking them read now would let them silently drop out of next run's unread-only ingest before that work happens.
   - If step 7's category apply failed for a row (mailbox error, connectivity, etc.), do not mark that row read even if its needs-reply is `No` -- an incompletely-processed email must stay unread so the next run picks it up again.
   - If the `mark-read` call itself fails for a row, do not treat it as fatal to the run -- report it explicitly in the triage report's Notes (which row, which error) rather than silently retrying or ignoring it. A failed mark-read just means that row stays unread and gets re-triaged next run, which is the safe direction to fail in.
   - `mark-read` is idempotent (setting a message already marked read to read again is a harmless no-op), so re-running this step against a row that got marked read by a previous partial run is safe and does not need a pre-check.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 8 | The full triage report (category, label, priority, reasoning, needs-reply per email), with any `Flag` rows called out separately along with why their age is ambiguous | Whether to recategorize, reprioritize, or resolve each `Flag` row to `Yes`/`No` (and flip any other needs-reply flags) before drafting begins. Stage 02 will not draft `Flag` rows the user hasn't resolved. This decision also determines which rows step 9 marks read as `No`, so it must resolve before step 9 runs. |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Category fidelity | Every applied category either matched an existing mailbox category or was explicitly confirmed by the user as new |
| Priority reasoning | Every priority score has a one-line reasoning that cites a specific rubric signal |
| Needs-reply coverage | Every unread email has an explicit needs-reply value: `Yes`, `No`, or `Flag` (not blank) |
| Staleness reasoning | Every `No` driven by age, and every `Flag`, has a one-line reasoning naming the message's age/date basis, not just "low priority" |
| Mark-read scoping | Every `No` row whose category apply succeeded is marked read after the checkpoint; no `Yes` or `Flag` row is marked read by this stage |
| Live-source fidelity | Every row's data (IDs, received date, categories, read state) came from this run's live fetch, with no carried-over or "unchanged" values. The report states the fetch time |
| Manual-change respect | No existing category on a message was overwritten without approval. Differences between live state and the resolved category are listed in Notes |
| Pre-mark-read re-verification | Every message was re-fetched live immediately before `mark-read`. Any that was moved, deleted, or unresolvable is named in Notes and not marked |
| Mark-read failure visibility | Any `mark-read` call that fails is named explicitly in the report's Notes (row + error), never silently dropped |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Triage report | `output/triage-report.md` | Markdown table: subject, sender, received date, entry ID, store ID, category, label, priority score + reasoning, needs-reply (`Yes`/`No`/`Flag`) |
| Updated category map | `../../shared/category-map.md` | Same file, updated in place with any new approved mappings |
| Outlook side effect | Inbox | Categories applied directly to messages via `outlookctl category set`; `No` rows marked read via `outlookctl mark-read` after the checkpoint resolves |
