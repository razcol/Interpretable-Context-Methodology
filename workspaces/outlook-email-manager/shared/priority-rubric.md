# Priority Rubric

Editable reference for scoring email priority during triage. Adjust weights or add senders anytime -- no need to re-run any setup.

## Signals (high to low weight)

1. **Urgency/deadline language** -- words like "asap", "urgent", "by EOD/tomorrow", explicit dates
2. **Direct question or action request addressed to the user** -- vs. FYI/CC-only
3. **Sender importance** -- see VIP Senders below
4. **Active existing thread** -- ongoing conversation vs. cold/new topic
5. **Time-sensitive content** -- imminent meetings, approvals blocking someone else's work

## Lowest Priority

Newsletters, automated notifications, FYI-only threads, large distribution lists.

## Message Age / Staleness (Reply Gate)

Age is checked separately from the priority score above -- it doesn't change how important an email *was*, it decides whether replying still makes sense *now*. Compare the message's `Received` date to today's date at triage time.

1. **Clearly stale -- skip, needs-reply = No.** The email is old enough (roughly a month or more, or tied to an event/deadline that has already passed -- e.g. "reminder: session on 13/05" when today is well past that date) that a reply would be out of place or the window to act has closed. Set needs-reply to `No` and note the reasoning as staleness, not just low priority. Do not draft a reply for these.
2. **Clearly current -- proceed as normal.** Recent messages (roughly within the last week, or an active back-and-forth thread regardless of the oldest message's date) are scored and flagged for reply per the signals above with no special handling.
3. **Ambiguous -- flag, do not decide silently.** Somewhere in between (roughly one to a few weeks old) with no clear signal that it's closed out (no later reply superseding it, no obviously-passed deadline, but also no confirmation it's still live) -- do not mark needs-reply `Yes` or `No` on your own judgment. Mark needs-reply as `Flag` and surface it to the user at the triage checkpoint with your reasoning for why you're unsure, so the user decides rather than the agent guessing. Never auto-draft a reply for a `Flag` row.

Guidance, not hard cutoffs -- a month-old email in a slow-moving VIP thread might still be worth a reply, and a three-day-old automated notice might already be dead. Use judgment, but when genuinely unsure, flag rather than guess in either direction.

## Manual Age Thresholds

Add notes here if you want firmer cutoffs than the guidance above (e.g. "always skip anything older than 2 weeks" or "my team never expects replies after 3 business days").

## VIP Senders

Firas, Alon

List names or email addresses that should bump priority regardless of content. Start empty and add over time -- this list is expected to grow as you use the workspace.

## Manual Adjustments

Add notes here about weight changes or exceptions you want the agent to remember.
