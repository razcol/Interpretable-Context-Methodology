---
name: session-extract
description: Searches past Cursor agent sessions on this machine across every project, filters them for a tool, skill, command, workflow, or failure, and writes a cited evidence brief used to change or design skills, tools, and workspaces. Use when the user passes this skill plus what to extract from earlier sessions. Do not use for a handoff of the current chat only (session-handoff).
disable-model-invocation: true
---

# Session extract

Finds past Cursor work on this computer and writes one cited brief. The brief recommends what to change in a skill, tool, or workspace. It does not edit those artifacts.

Transcripts are not in the git repo. They live at `~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>.jsonl`. A search from the current workspace misses the other projects.

## Inputs

The user passes this skill and what to extract. Optional: marker strings, a product path to compare against, project slugs, and whether subagents are in the candidate scan.

If the user gives no markers, derive two to five specific strings (a command name, a path, an env var, a skill filename). State them before scanning. A single vague word over-matches. The script does not invent markers.

## Process

1. Restate the request and the markers. Escape regex metacharacters in literal markers.
2. Run the scanner from any working directory. Do not Grep the jsonl tree as the first pass.

```bash
python3 <skill-folder>/scripts/scan_transcripts.py \
  --pattern '<marker>' --pattern '<marker>'
```

`<skill-folder>` is the folder containing this file. Add `--project <slug>` to limit, or `--include-subagents` only when the user asked for subagent files in the candidate set. The script prints a coverage JSON line, then one JSON line per match. It matches the raw jsonl line, so a marker that appears only in a tool argument still counts. Excerpts are decoded user text, redacted and truncated, not the raw JSON. Exit 2 means a bad regex or a missing `~/.cursor/projects`. Zero matches is a successful empty result: still write the report.

3. Label each match core, partial, or incidental. A regex hit is not usage. Discard incidental matches before deep reading. In Coverage, state how many were discarded and give one example uuid and the reason.
4. If more than about eight core or partial parents remain, split an explicit path list across read-only subagents. Each brief includes the report headings, the redaction rules, and the instruction not to scan every project again. One subagent may inventory the product path. Transcript subagents only cite sessions.
5. Deep-read with the excerpts plus a ranged read of the jsonl. Do not load a multi-megabyte line into context. Tool results in these files are often missing. Confirm outcomes from later assistant text and, when a product path was given, from the current files.
6. Open `subagents/` only when that parent is about building the thing, the parent jsonl is missing (the coverage line lists orphans), or the user asked. The coverage `orphans` array is session folders with no parent file.
7. Write the report to `session-extract-<YYYY-MM-DD>-<topic-slug>.md` in the working directory, using [references/report-template.md](references/report-template.md). If the name exists, use `-2`, then `-3`. Never overwrite. Write the file before the final chat message.
8. Tell the user the path, the coverage counts, three to seven findings, and what was not searched.

## Rules

- Never print or write secret values. The script redacts `figd_…`, bearer tokens, JWTs, `password=`, long base64, and `data:` URLs, and it omits `store.json` bodies. If a ranged read still shows a secret, leave it out of the report.
- Do not read `state.vscdb`, `~/.cursor/chats/*/store.db`, or agent-store sqlite. Do not use `conversation-search.db` as the only search. Say in Coverage that those stores were not read.
- Do not claim sessions from another machine or from the Windows Cursor profile were included.
- Separate "still open" from "a later session or the current code already fixed it."
- Recommendations only. Do not edit the skill, tool, or workspace named in Implications.
