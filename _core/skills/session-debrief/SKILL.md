---
name: session-debrief
description: Explains one agent session (Cursor or Kiro CLI) to the human who must decide about it. Writes a short debrief that answers the user's real question first, explains the mechanism in plain words with a small chart, lists each decision the user owns with a recommendation, lists what was left undone and why, and pre-answers the follow-up questions. Use when the user passes a session id (or says "this session" or "the last session") and wants to understand, review, or decide on that agent's work. Not for a handoff to another agent (session-handoff) or for mining many sessions to change a tool (session-extract).
---

# Session debrief

The reader designed the task but did not watch the work. They need to understand it well enough to decide, and they usually do not know which questions to ask. The debrief asks and answers those questions for them.

Read-only. Never edit the session's code, branches, tickets, or PR.

## Inputs

- A session id: full uuid or a unique prefix of at least 6 characters. Or `--latest` for the newest session in a directory. If the user means the chat you are in, debrief it from your own context and skip step 1.
- Optional: a focus ("the Rovo comments", "is it safe to push") and a repo path.

## Process

1. **Load the digest.** It prints to stdout. Save it under `/tmp`, never beside the debrief, and read it in chunks if your reader caps length. The Files touched table has a `present` column: `no` means that path is gone now.

   ```bash
   S=<skill-folder>/scripts
   python3 $S/session_digest.py <id>                       # whole session, about 10-40k chars
   python3 $S/session_digest.py --latest --cwd <dir>
   python3 $S/session_digest.py <id> --turn 7 --final-only # one turn's ask and answer in full
   python3 $S/session_digest.py <id> --subagent 3          # one subagent's full report
   ```

   `<skill-folder>` is the folder holding this file. Exit 2 means not found; exit 3 means an ambiguous prefix (ask the user which match). When text you need is cut (`[…]`), use `--turn`, not the raw jsonl. The digest also lists later sessions that mention this one; read their first lines, because they are often the user's own follow-ups and may have changed or decided things.

2. **Find the user's real question.** Read every real user turn; the goal often arrives in turn 2 or 3, or shifts after a `/clear`. If the user named a focus, that is the question. If they only said "debrief this", the question is "what happened, and what must I decide?". Classify the session with [references/session-types.md](references/session-types.md). Its "Must also cover" items are mandatory.

3. **Check against the repo.** Use the digest's `Working dirs` line. If a worktree is gone, use the main checkout with `git -C <repo>`. Check cheaply:
   - **Claims.** Cursor stores no tool results, so "tests passed" stays *reported* unless you see evidence (a commit with tests, a file, a log).
   - **After the session.** `git log --since=<last session date> --all --oneline`, `git branch -a --contains <commit>`, `git merge-base --is-ancestor <commit> <branch>`. Later commits can close open items or change the bottom line. Name the author `git log` prints. Attribute the commit to a later session from step 1 when one matches. Write "author unknown" only when the log has no author.
   - **Missing files.** When `present` is `no`, say the path is gone. Check `git status`, reflog, stash, and gitignored build copies before calling the work lost. A branch name that no longer exists is not a dead end: `git log --all --since=<date>` still finds the merge.
   - **Introduced or pre-existing**, for every issue or reviewer point: `git diff $(git merge-base <base> <head>)..<head>` decides. Say "introduced" or "already there" in the debrief. Pre-existing items get one line, not a decision card.
   - **Precedent.** For a review or design verdict, find one file in the same codebase that already follows or breaks the pattern, and cite `file:line`.
   - **Remotes** before any push decision: `git remote -v`.
   If a cause was never found, write "cause unknown" and name the missing evidence.

4. **Explain the mechanism.** Write `## How it works` around what the user must understand before deciding: one concrete example from the session, the steps in plain words, and a Mermaid chart of that mechanism. The red node is the constraint (what the framework or product cannot do), not the workaround the agent built. For a design question, this section also states the visitor-visible effect: status code, what the user sees when it fails, and caching. Chart the session timeline only when the confusing part is what the agent did.

5. **List decisions and items left undone.**
   - Decisions: open questions the agent asked, options it offered, reviewer comments, unrequested changes, risky steps (push, delete, deploy, rotate a secret), things the agent said should change but did not. Only decisions still open today; only ones that affect the user's goal.
   - Left undone: everything deferred, skipped, or called a follow-up, by the parent or by any subagent. For orchestration, one row per hand edit a subagent listed, including rows the parent's close does not repeat. Quote the reason from the turn that states the scope ("too much scope"), not only a closing "if you want". Give the status now. Open items need both "do it if" and "skip it if". An item the agent called "not a gap" is one plain sentence and never has status `open`.

6. **Predict the follow-ups.** Read [references/follow-up-questions.md](references/follow-up-questions.md). Answer the 4 to 7 questions this user would most likely ask next, answer first, with the session type's "Must also cover" items first.

7. **Write the debrief** to `session-debrief-<today YYYY-MM-DD>-<topic-slug>.md` in the working directory, using [references/debrief-template.md](references/debrief-template.md). Add only the optional sections the template's table calls for. Add `-2`, `-3` if the name exists. Never overwrite.

8. **Check it.** Run `python3 $S/check_debrief.py <file>` after the file is written. Fix every ERROR and rerun until it prints OK. Fix each WARN unless you have a reason to keep it.

9. **Optional editable chart.** On request, build an Excalidraw file of the same flow with `_core/skills/system-flowcharts`.

10. **Reply in chat** with the file path, the bottom line, and the decisions as a numbered list with your recommendation for each. Offer to take them one at a time. If the user answers by number ("1 yes, 2 skip"), append their answers under `## Your answers`.

## Writing rules

- Answer the user's question in the first sentence, in plain words. A review gets "Yes." or "No." for each claim in that first sentence, including which values to add and which to leave. A yes/no question gets "Yes." or "No." first. Do not retell the session before the answer.
- Explain a project term in brackets the first time it appears, with the real example.
- One claim per sentence and one verdict per item. If the agent changed its verdict during the session, say so once and give the final one.
- When something was removed or replaced, say what replaced it. For each option, say what it does not fix.
- Keep separate issues separate and numbered.
- Code only as a short snippet that makes the point, with a one-line comment.
- No process narration or coverage numbers.
- Never print secret values. If the digest reports secret-like values in tool output, check whether a real secret was exposed; if so, say where and make rotating it a decision.
- Write in the language the user used in the session unless asked otherwise. A reply meant for a reviewer goes in the reviewer's language.
