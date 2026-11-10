# Report template

This is the shape of the chat reply. Do not write it to a file unless the user explicitly asks to save this brief.

Keep section titles exact. Cite a transcript uuid on every claim in Keep, Extra or harmful, and Still missing. A uuid with no parent jsonl is listed under Gaps, not as a normal session.

## Request and markers

One paragraph restating the extraction request. Then the markers actually passed to `scan_transcripts.py`. If the agent derived them, say so.

## Coverage

- Projects root and slug count
- Parent transcripts scanned, files matched, files discarded as incidental (with one example uuid and why)
- Subagent files opened, and why
- Orphan session folders (parent jsonl missing), count and uuids
- Stores not read: `state.vscdb`, `~/.cursor/chats/*/store.db`, agent-store sqlite, and that `conversation-search.db` was not the search

## Sessions

One bullet per kept session (core, partial, or incidental that the user would still want to see). Skip the discarded incidental pile beyond the one example in Coverage.

- `uuid` — project slug — date — core | partial | incidental — one sentence — short user quote — transcript path

## Keep

Behavior that worked and should stay. Note when a later session already fixed an earlier complaint.

## Extra or harmful

What agents did that the user had to undo, or that the current product files show is wrong.

## Still missing

Ordered by how often sessions hit it. Mark each item still open or already fixed in a later session or in the current code. Do not present a shipped fix as still missing.

## Out of scope

Asked once and explicitly deferred, or outside the product the user named.

## Implications

Concrete changes to a named skill, tool, or workspace. Recommendations only. No patches, no file edits.

## Gaps

Missing parent jsonl, redacted tool results, sessions that exist only on another machine, markers that may have missed a real session.
