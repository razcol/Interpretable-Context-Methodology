# Handoff Document Template

Copy the structure below. Keep the section titles and numbers exactly as written: `scripts/check_handoff.py` relies on them. Replace every `<...>` and every italic instruction. Any section with nothing to report says `None.` plus a one-line reason. Never delete a section.

````markdown
# Handoff: <short title of the work>

- **Work status:** IN PROGRESS | BLOCKED | PAUSED   <pick one; this work is NOT finished>
- **Created:** <timestamp with timezone, from gather_state.py>
- **Working directory:** <absolute path the session ran from>
- **Written by:** <agent/tool name if known, else "an AI agent session">
- **Repository state:** <branch @ short HEAD, clean/dirty -- or "not a git repository">

> **Reader, start here.** This document was written at the end of a session whose conversation you cannot see. The work described is unfinished. Everything you need to continue is below. Treat recorded decisions as settled unless the user reopens them. Statements marked *(verified)* were checked at writing time; statements marked *(reported)* come from the conversation only. Re-check anything marked *(reported)* that your next step depends on.

## 1. Goal

*What is being accomplished and why. Then the definition of done: concrete, checkable conditions under which this work is finished.*

## 2. Status

*Three to six sentences: the overall state right now, in plain words. Which part is done, which is mid-flight, what is untouched, and the single most important thing to know. Say what has been tested and what has not.*

## 3. Work Breakdown

| State | Item | Detail / evidence |
|-------|------|-------------------|
| DONE | <item> | <what exists; how it was checked (verified/reported)> |
| IN PROGRESS | <item> | <exactly where it stopped; what is half-finished> |
| NOT STARTED | <item> | <why it is needed; any dependency> |

## 4. Decisions

*Each decision as: **Decision** -- reasoning -- who decided (user / agent). Include the alternatives that were weighed if they matter. Mark anything the user explicitly chose.*

## 5. Rejected Approaches

*Each dead end as: **Approach** -- why it failed or was dropped -- what evidence showed it. Prevents the next session from repeating it.*

## 6. Constraints and Preferences

*Hard constraints (environment, permissions, rules the user set) and the user's stated preferences (style, tone, process). Quote the user's exact words where wording matters, in blockquotes.*

## 7. Files and Artifacts

| Path or link | Role | State | Read order |
|--------------|------|-------|------------|
| <path/URL> | <what it is and why it matters> | created / modified / reference-only / external | 1 |

*State the content that matters when it is short enough to be useful here; otherwise say what the file holds. A reader must understand the work without opening the files, and know which to open first.*

## 8. Commands and Results

*Commands, queries, or actions that mattered, with the outcome of each, including failures and their exact error text. Omit routine noise. Redact any secret values.*

## 9. Open Questions and Blockers

*Each item: the question or blocker -- who can resolve it (user / external party / the next agent) -- what is blocked by it -- any current leading guess.*

## 10. Next Steps

*Ordered. Step 1 must be executable without asking anything: name the file, the command, or the exact question for the user. For each step, say how to tell it worked. Put any "verify before continuing" checks first.*

1. <step> -- done when: <check>

## 11. Environment and Tooling

*Tools, versions, services, accounts, environment variables, and config the work depends on. Names and locations only. Never values. Note anything that must be set up before continuing and anything that only works on the original machine.*
````

## Writing rules

- **Self-contained.** No "as discussed", "the above", "that file". Name things. Give paths relative to the stated working directory or absolute.
- **Honest state.** Separate what was verified from what was only reported. Do not describe planned work as done. Untested means say untested.
- **Reasoning over narration.** Record why, not the chronological story of the chat.
- **Map, not copy.** Reference artifacts by path/link and say what matters about them. Do not paste long files or logs.
- **No sensitive information.** No passwords, tokens, API keys, private keys, connection strings with credentials, cookies, or personal data. Refer to them by name and where they live (for example "the `JIRA_API_TOKEN` environment variable"). If the user pasted a secret in the session, do not repeat it; say that one was shared and should be rotated.
- **Nothing silently dropped.** If a section has nothing, write `None.` with the reason.
- **Procedures and criteria travel with the document.** If a next step depends on a procedure, test protocol, or acceptance criteria that live in another file, summarize the essential points inline and name the file for the rest. A reader should not need to open it just to know what "done" means.
- **Absolute paths in the Files table**, so the reader needs no assumptions about the base directory.
- **System facts are pasted, not typed.** Use the timestamp and repository state printed by `gather_state.py` verbatim.
- **List what else sits beside the work.** If scratch, test, or output folders were created during the session, name them in the Files table with their purpose, so the reader can tell deliberate artifacts from leftovers.
