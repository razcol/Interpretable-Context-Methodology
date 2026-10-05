---
name: session-handoff
description: Writes a self-contained handoff document from the current session so unfinished work can be continued later or in another session that cannot see this conversation. Use only when the user asks for a handoff, session report, or context document to continue the work elsewhere.
---

# Session Handoff

Turns the current session into one markdown file that a reader with no access to the conversation can pick up and continue from. On-demand only. The user points the next session at the file manually.

## Process

1. **Name the work.** Pick a short topic (3 to 6 words) that identifies the unfinished work. If the session covered several workstreams, cover all unfinished ones in the one document and list each as its own item in section 3.
2. **Get verified facts.** Run `python3 <skill-folder>/scripts/gather_state.py "<topic>"` with the shell's working directory set to the directory the session runs in (`<skill-folder>` is the folder containing this file; the script reports facts about the directory you run it from). It prints the working directory, timestamp, a collision-safe `target_file` in that directory, and git state when there is a repository. Paste these values into the document verbatim; never type a timestamp from memory. If Python is unavailable, get them by hand (`date -Iseconds`, `pwd`, `git status --short`), name the file `session-handoff-<YYYY-MM-DD>-<topic-slug>.md`, and never overwrite an existing file.
3. **Mine the whole conversation**, including early turns, not only the recent ones. Collect:
   - the goal and the definition of done
   - what is done, in progress, and not started
   - every decision and its reason, and who made it
   - approaches tried and dropped, with the evidence
   - user constraints and preferences, and user instructions whose exact wording matters (quote them)
   - every file and artifact touched or discussed, with its state
   - commands and results that mattered, failures included
   - open questions and blockers
   - environment and tooling dependencies
4. **Verify what you can.** Before claiming something exists or works, check it: list the files, re-read the key lines, re-run a cheap check. Mark each claim *(verified)* or *(reported)* in the document. Never present planned work as done.
5. **Write the document** to `target_file` using the structure in [references/template.md](references/template.md). Follow its writing rules. Keep the section titles exact.
6. **Check it.** Run `python3 <skill-folder>/scripts/check_handoff.py <target_file>`. Fix every ERROR and rerun until it passes. Review WARN lines by judgment. Then re-read the whole document once for sensitive content the patterns cannot catch.
7. **Cold-read test.** Imagine you have never seen this conversation. Can you answer, from the document alone: Is this finished? Where did it stop? What was decided and why? What is step 1, and how do I know it worked? If any answer is missing, fix the document.
8. **Report to the user**: the file's path, a two or three sentence summary of the state, and anything you could not verify. Do not repeat secrets. If a secret was shared in the session, say so and recommend rotating it.

## Rules

- Never include secret values or personal data: passwords, tokens, keys, cookies, connection strings with credentials. Refer to them by name and location only.
- Reference other artifacts by path or link, and say what matters about each. Do not paste long files or logs.
- Always write a new file. Do not update or merge into an earlier handoff unless the user asks.
- If the work is actually finished, tell the user instead of writing a handoff that claims it is unfinished.
- This skill writes the document only. It does not resume work from one, or search for earlier handoffs.
