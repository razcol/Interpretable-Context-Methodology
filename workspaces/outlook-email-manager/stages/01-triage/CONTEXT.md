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

## Process

1. List unread emails: `outlookctl list --folder inbox --unread-only`.
2. For each email, pull prior thread context via `outlookctl search`/`get` if the subject/sender indicates an ongoing conversation.
3. Fetch the mailbox's defined categories: `outlookctl category list`. Match each email to an existing category where reasonable. If no good match exists, suggest a new category rather than inventing one silently -- flag it in the report for the user to confirm.
4. Update `shared/category-map.md` with any newly approved matches or suggestions from this run.
5. Score priority per `shared/priority-rubric.md`: urgency/deadline language, direct ask vs. FYI, sender importance/VIP list, active thread, time-sensitive content. Newsletters/automated/mass-distribution default low.
6. Check message age against today's date per the "Message Age / Staleness" section of `shared/priority-rubric.md`, and set needs-reply to one of three values:
   - `No` -- clearly stale (old, or tied to a passed date/event). Do not draft.
   - `Yes` -- clearly still worth a reply (recent, or an active thread).
   - `Flag` -- ambiguous age with no clear signal either way. Do not decide on the agent's behalf; this row gets surfaced to the user at the checkpoint below instead of being auto-drafted.
7. Apply the resolved category back onto the message: `outlookctl category set --id <id> --store <store> --categories "<name>"`.
8. Write the triage report, including each email's entry ID and store ID (needed later for mark-read -- see step 9 and stage 02).
9. **After** the checkpoint below is resolved (category suggestions confirmed, any needs-reply flips applied) mark as read only the rows whose needs-reply is `No`: `outlookctl mark-read --id <id> --store <store>`. Triage is the last stage that will ever touch a `No` row, so this is where "completely done" happens for it.
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
| Mark-read failure visibility | Any `mark-read` call that fails is named explicitly in the report's Notes (row + error), never silently dropped |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Triage report | `output/triage-report.md` | Markdown table: subject, sender, received date, entry ID, store ID, category, label, priority score + reasoning, needs-reply (`Yes`/`No`/`Flag`) |
| Updated category map | `../../shared/category-map.md` | Same file, updated in place with any new approved mappings |
| Outlook side effect | Inbox | Categories applied directly to messages via `outlookctl category set`; `No` rows marked read via `outlookctl mark-read` after the checkpoint resolves |
