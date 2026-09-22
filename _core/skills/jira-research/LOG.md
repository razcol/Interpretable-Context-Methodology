# Jira Research -- Working Log

Append-only log of attempts to connect to / extract data from Jira. Newest
entry at the bottom. See `SKILL.md` for what to record.

Do not put credentials or tokens in this file.

---

## Template for new entries

```
### YYYY-MM-DD -- [short description of the task]

- **Goal:** what info you needed and from where (issue key, project, JQL, etc.)
- **Approach tried:** A (MCP) / B (REST API) / C (CLI) / other
- **Details:** exact command or tool call used
- **Result:** worked / partially worked / failed
- **Friction:** auth issues, pagination, ADF parsing, rate limits, etc.
- **Would reuse as-is?** yes / no / with changes -- [what changes]
```

---

### 2026-09-22 -- find most recently updated issue in project MAIN

- **Goal:** find the most recent Jira task (first live test of this skill), project `MAIN`, site `switchil.atlassian.net`.
- **Approach tried:** B (REST API), no MCP server or CLI (`jira`/`acli`) installed/configured in this environment -- confirmed via `command -v` and checking `~/.kiro/settings/mcp.json` (absent) before falling back to REST.
- **Details:**
  - Auth: Basic Auth, `email:api_token` (Jira Cloud API token from https://id.atlassian.com/manage-profile/security/api-tokens).
  - First tried documented endpoint `GET /rest/api/3/search` with JQL `project=MAIN ORDER BY updated DESC` -> **HTTP 410 Gone**. This endpoint was fully shut down by Atlassian between Aug-Oct 2025 (all traffic blocked as of Oct 31 2025).
  - Correct current endpoint: `GET /rest/api/3/search/jql` -- same auth, same JQL param, but:
    - Response only returns `id` unless you explicitly pass `fields=...` as a query param.
    - Pagination changed: no more `startAt`/`total`, instead `nextPageToken` + `isLast` boolean (token-based, not offset-based).
  - Working call:
    ```bash
    curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Accept: application/json" \
      -G --data-urlencode "jql=project=MAIN ORDER BY updated DESC" \
      --data-urlencode "maxResults=1" \
      --data-urlencode "fields=summary,status,assignee,updated,created,issuetype,priority" \
      "$JIRA_BASE_URL/rest/api/3/search/jql"
    ```
- **Result:** worked. Found `MAIN-4328`, a High-priority Bug in Backlog, unassigned, updated same-day.
- **Friction:**
  - The `SKILL.md` draft (approach B) referenced the now-dead `/rest/api/3/search` endpoint -- needs updating to `/rest/api/3/search/jql`.
  - `search/jql` needs an explicit `fields` param or you only get issue IDs back -- easy to miss.
  - Issue content (summary) was in Hebrew -- confirms this Jira instance is not English-only; don't assume ASCII/English text when parsing fields downstream.
  - No MCP server or CLI configured at all in this environment -- REST + manual token was the only viable path this time.
  - User pasted the raw API token directly into chat rather than exporting it as an env var themselves. Functionally worked but is a credential-hygiene risk (token now in conversation history) -- flagged to user, recommended revoking/rotating after this test.
- **Would reuse as-is?** Yes, with changes -- fix the endpoint URL in SKILL.md, document the `fields` requirement and new pagination shape, and add a note that a local `.env` (gitignored) should hold `JIRA_BASE_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` instead of pasting tokens into chat.

---

### 2026-09-22 -- scouting round: ACLI vs REST vs MCP for the same query

- **Goal:** compare official Atlassian CLI (ACLI) against REST API (already confirmed) and scout the official MCP server, to find the lowest-friction option going forward. Same test query: most recently updated issue in project MAIN.
- **Approach tried:** C (ACLI), researched but did not yet test A (Atlassian Rovo MCP server, `https://mcp.atlassian.com/v2/mcp`).
- **Details:**
  - Install (Linux x86_64, WSL2, no root needed):
    ```bash
    mkdir -p ~/.local/bin
    curl -sL -o ~/.local/bin/acli "https://acli.atlassian.com/linux/latest/acli_linux_amd64/acli"
    chmod +x ~/.local/bin/acli
    ```
  - Auth (non-interactive, token piped via stdin -- do not pass token as a CLI arg, it would show in shell history/process list):
    ```bash
    echo "$JIRA_API_TOKEN" | acli jira auth login --site "switchil.atlassian.net" --email "$JIRA_EMAIL" --token
    ```
  - Query:
    ```bash
    acli jira workitem search --jql "project = MAIN ORDER BY updated DESC" --limit 1 --json
    ```
  - **Execution gotcha (environment-specific, not an ACLI bug):** in this sandboxed shell, ACLI's spinner/interactive output during `auth login`, and even a plain `--help` call, appeared to hang or return nothing on the first few attempts. Root cause was output-buffering/streaming behavior of the tool-calling environment, not ACLI itself. Fix: always redirect stdout/stderr to files (`> out.log 2>err.log`) and read the files back afterward instead of relying on live/streamed terminal output, and wrap long-running calls in `timeout`. Once redirected to files, every call returned correctly and no process was left running (`ps aux | grep acli` clean).
- **Result:** worked, and matched the REST result exactly -- same issue (`MAIN-4328`), same field values (title, status, priority, assignee).
- **Friction:**
  - Requires a one-time binary install (no apt package in this distro's default repos; used Atlassian's direct binary download instead). Small one-time setup cost, not a per-call cost.
  - Auth is a separate persistent step (`auth login`), stored locally by ACLI -- once done, no need to pass credentials on every call, which is nicer than REST's per-call Basic Auth header.
  - Default `--fields` already includes the useful set (`issuetype,key,assignee,priority,status,summary`) without needing to specify them, unlike REST's `search/jql` which returns bare IDs unless `fields` is passed explicitly.
  - `--json` output is easy to parse and less verbose to request than the REST equivalent.
- **Would reuse as-is?** Yes. Lower friction than REST per-query (no manual auth header, better defaults) at the cost of a one-time install + login step. Good candidate for "settled approach" pending an MCP comparison.
- **Still to test:** Atlassian Rovo MCP server (`https://mcp.atlassian.com/v2/mcp`) -- OAuth 2.1 or API token, consumes Rovo credits per call (cost consideration), officially supported by many AI clients but needs to be added via this project's MCP config to test in this environment.

---

### 2026-09-22 -- routine use: list recent issues, then view + comments on one issue (ACLI)

- **Goal:** exercise the settled ACLI approach on the untested surface area called out in SKILL.md -- issue view with full fields, and comments -- not just JQL search. Same project (`MAIN`), site `switchil.atlassian.net`. Also a chance to retest after a prior session ended early due to a tool-call syntax error (`view --key`), per user request to "try again to overcome this safely."
- **Approach tried:** C (ACLI) only. Auth was already persisted from the prior session (`acli jira auth login` was not re-run) -- confirmed live with `acli jira auth status` before querying.
- **Details:**
  - Auth check (no credentials passed, reads persisted session):
    ```bash
    timeout 25 acli jira auth status > out.log 2>&1
    ```
    Result: `✓ Authenticated / Site: switchil.atlassian.net / Email: raz.c@colmobil.co.il / Authentication Type: api_token`. Confirms ACLI auth persistence across sessions/days, as SKILL.md claims.
  - Search, 10 results instead of 1 (first session only tried `--limit 1`):
    ```bash
    timeout 25 acli jira workitem search --jql "project = MAIN ORDER BY updated DESC" --limit 10 --json > out.log 2>&1
    ```
    Result: worked, returned 10 full issues.
  - **Correction to prior log entry:** the 2026-09-22 scouting entry above says ACLI's `--json` search output is "less verbose" than REST and implied a compact default field set. That is **not accurate** -- `workitem search --json` returns the full nested issue object per result (issuetype, priority, status incl. statusCategory, assignee incl. avatarUrls, etc.), same shape as raw REST, not a slim default. The "less verbose to request" point (no need to pass `fields=`) still holds -- only the "less verbose output" characterization was wrong. Flagging here rather than silently editing the old entry, since this log is append-only; SKILL.md wording should be adjusted to stop implying the output itself is trimmed.
  - **First attempt failed -- root-caused, not a dead end:**
    ```bash
    acli jira workitem view --key MAIN-4338 --json
    ```
    -> `✗ Error: unknown flag: --key`. Checked `acli jira workitem view --help`: the key is a **positional argument**, not a flag (`acli jira workitem view [key] [flags]`). This is a real, useful gotcha to document -- not an auth/env/environment issue like the earlier "hanging output" gotcha.
  - Corrected call:
    ```bash
    timeout 25 acli jira workitem view MAIN-4338 --fields summary,comment,status,assignee,description --json > out.log 2>&1
    ```
    Result: worked. Returned full issue incl. `description` in ADF (Atlassian Document Format, nested `content`/`paragraph`/`text` nodes) and an embedded `comment` block (`{comments: [], total: 0}` for this issue) in a single call -- no separate comment-fetch needed when using `view --fields ...,comment`.
  - Also tried the dedicated comment subcommand directly, which worked on the first try (unlike `view`):
    ```bash
    timeout 25 acli jira workitem comment list --key MAIN-4338 --json > out.log 2>&1
    ```
    Result: worked, returned `{"comments": [], "isLast": true, "maxResults": 50, "startAt": 0, "total": 0}`. Note the inconsistency: `comment list` **does** accept `--key`, while `view` does **not** -- flag conventions are not uniform across `workitem` subcommands. Don't assume one subcommand's flag shape applies to another; check `--help` per subcommand.
  - Output-capture gotcha recurrence: every command in this session, including plain `echo hello` with no acli involved, returned exit code -1 with a stray shell-prompt fragment appended to captured output, in what looks like a harness/terminal-wrapper quirk distinct from the documented ACLI spinner-buffering issue. Workaround was the same either way: redirect to a log file (`> out.log 2>&1`) and read the file back with a separate command instead of trusting the live/streamed output or the reported exit code. This worked 100% of the time this session -- exit code was unreliable, but file contents were always correct once written.
- **Result:** worked (search, comment list, and view all confirmed) after one corrected syntax error.
- **Friction:**
  - `view` takes the issue key positionally, not via `--key` -- easy mistake, worth calling out explicitly in SKILL.md's ACLI reference section so it isn't rediscovered.
  - Flag shape differs between `workitem view` and `workitem comment list` (positional vs `--key`) -- per-subcommand `--help` is genuinely necessary, can't extrapolate.
  - Exit codes from the shell tool were unreliable all session (-1 on success and no distinguishing signal for failure); only reliable signal was the redacted log file content. Not an ACLI issue, but relevant for anyone scripting around it in a similar sandboxed/wrapped shell.
  - Corrected a prior log claim (see above) about `--json` search output being more compact than REST -- it isn't; only the request side is simpler.
- **Would reuse as-is?** Yes, with two SKILL.md documentation additions: (1) `workitem view KEY` takes the key positionally, and (2) `--fields ...,comment` on `view` can fetch description + comments in one call, as a lower-friction alternative to a separate `comment list` call when you already need other fields too.

---

### 2026-09-22 -- list all projects and boards (new surface: `project`/`board`, not `workitem`)

- **Goal:** user asked to list all projects/boards visible to the account -- first time this skill has been used for anything other than issue-level data (search/view/comments). Same site, `switchil.atlassian.net`.
- **Approach tried:** C (ACLI) only.
- **Details:**
  - Discovered subcommands via `--help` rather than guessing, since this is untested surface:
    ```bash
    acli jira project --help   # -> list, view, create, update, delete, archive, restore
    acli jira board --help     # -> search, list-projects, list-sprints, view, create, delete, get (deprecated)
    ```
  - Checked flags before running anything (`acli jira project list --help`, `acli jira board search --help`) -- neither has a required flag, both are safe to run with no filters for a full read-only listing.
  - Projects:
    ```bash
    timeout 25 acli jira project list --paginate --json > out.log 2>&1
    ```
    Result: worked. Returned 31 projects. **Note:** unlike `workitem view`/`search`, `project list --json` has **no default trimmed field set and no `--fields` flag at all** -- it always returns the full raw project object (avatarUrls at 4 sizes, full lead user object, every nullable field, etc.) for every project. Output was large enough (>30k chars) that it needed a follow-up `python3 -c "..."` pass reading the same JSON file to extract just `key`+`name` for a usable summary, rather than trying to eyeball the raw dump. Worth knowing up front next time rather than being surprised by the size.
  - Boards:
    ```bash
    timeout 25 acli jira board search --paginate --json > out.log 2>&1
    ```
    Result: worked, first try, no flag mistakes this time (checked `--help` before calling, unlike the `view --key` miss last session). Returned 24 boards, each with `id`, `name`, `type` (kanban/scrum/simple), and `location` (a `"Project Name (KEY)"` string, not a separate key field -- if you need just the project key, you must parse it out of `location` yourself, e.g. via a regex on the parenthesized suffix).
  - Cross-check: 31 projects but only 24 boards -- confirms not every project has a board (expected for `business`-type / non-software projects, several of which showed up in the project list with `"projectTypeKey": "business"`).
  - Exit-code/output-capture quirk recurred again, consistent with prior sessions: every command reported exit code -1 or showed a trailing shell-prompt fragment in captured output, including plain commands like `wc -l` and `test -s ... && echo ok`. Redirecting to a file and reading it back (or using `test -s file && echo` as an explicit content-presence check) remained 100% reliable regardless of the reported exit code. Given this has now recurred across three separate sessions today, this looks like a property of this specific sandboxed/wrapped shell environment (not ACLI, not this skill) -- worth remembering as a standing fact about this environment rather than re-diagnosing it each time.
- **Result:** worked cleanly, no failed calls this time (checking `--help` first before calling avoided repeating the earlier `view --key` mistake).
- **Friction:**
  - `project list` returning the full raw object with no `--fields`/slim option is a real gap compared to `workitem view`/`search` (which at least have a `--fields` flag even if search ignores it for filtering purposes) -- for a large Jira instance this could get unwieldy; piping through `jq`/`python3` for extraction is the practical answer, not a skill failure.
  - `board search` has no issue -- it returns a reasonably-sized, already-useful shape (id/name/type/location) without needing a fields flag.
  - Project key is embedded inside `location`'s string on boards, not a separate JSON field -- minor parsing tax if scripting against this.
- **Would reuse as-is?** Yes. Add a short "listing projects/boards" subsection to SKILL.md's reference section (separate from the `workitem` reference) so `project list` / `board search` don't need rediscovering via `--help` next time, and note the "no `--fields` on `project list`, expect a large raw dump" gotcha there.



---

### 2026-09-22 -- real use case: issues assigned to me, across all projects (skill-factory maintenance test)

- **Goal:** first test of this skill run explicitly through the skill-factory maintenance workflow (stage 04-draft-and-test, existing mode). Real day-to-day use case supplied by the user: "what's assigned to me?" -- no project specified.
- **Approach tried:** C (ACLI) only, settled approach run as-is.
- **Details:**
  - Confirmed auth still persisted: `acli jira auth status` -> authenticated, no re-login needed.
  - `acli jira workitem search --jql "assignee = currentUser() ORDER BY updated DESC" --limit 20 --json` -> exactly 20 results, no in-band signal whether that was the full set.
  - Re-ran with `--limit 100` -> 39 total results, split across **two** projects (`MAIN`: 12, `LUX`: 27) -- first time this skill's JQL omitted a `project = ...` clause entirely.
  - Parsed with a short `python3` script (not eyeballed) to get a status breakdown ({Done: 36, In Progress: 1, To Do: 1, Backlog: 1}) and a 3-row "open issues" table.
  - Exit-code/output-capture quirk reproduced again on every call this session, **including a bare `echo hello` with no ACLI involved**, run as a deliberate control test. Same workaround as documented (redirect to file, ignore reported exit code, read file back) worked 100% of the time.
- **Result:** worked. Produced a correct, verified 3-issue "currently open, assigned to me" answer (MAIN-4246, MAIN-4251, MAIN-4283) out of 39 total assigned issues across 2 projects.
- **Friction:**
  - `--limit 20` silently returned a partial result set with zero indication it was partial -- genuinely easy to under-report "everything assigned to you" if you don't think to raise the limit. Documented in SKILL.md as a named gotcha.
  - Cross-project JQL (no `project =` clause) was previously listed as untested in SKILL.md; it worked with no extra effort at all -- SKILL.md updated to reflect this as confirmed rather than open.
  - Control test (`echo hello > file 2>&1`, checked separately) reproduced the exact same fake exit-code -1 / stray-prompt-fragment symptom as ACLI calls in this same session -- further confirms this is a property of this sandboxed shell wrapper, unrelated to ACLI or this skill. No new mitigation needed; existing file-redirect workaround holds.
- **Would reuse as-is?** Yes. Two SKILL.md additions made from this session: (1) a named cross-project "my issues" example using `assignee = currentUser()`, and (2) an explicit warning that `workitem search --json` has no total/isLast indicator, so a full page of `--limit N` results is not proof that N is the true count.

---

### 2026-09-22 -- attachment metadata (new surface: `workitem attachment`, part of skill-factory maintenance test)

- **Goal:** exercise attachments, one of the explicitly untested gaps called out in SKILL.md's status line. Real issue with an actual attachment, found via JQL rather than guessing: `assignee = currentUser() AND attachments is not EMPTY`.
- **Approach tried:** C (ACLI) only.
- **Details:**
  - `attachments is not EMPTY` JQL clause worked first try, returned 20 of the user's issues that have at least one attachment (out of 39 total assigned).
  - Picked `MAIN-4251` and pulled attachment data two ways:
    1. `acli jira workitem view MAIN-4251 --fields summary,attachment --json` -> full attachment object: `id`, `filename`, `size`, `mimeType`, `author` (full user object), `created`, `content` URL, `thumbnail` URL, `self` URL.
    2. `acli jira workitem attachment list --key MAIN-4251 --json` -> trimmed shape: only `id`, `name`, `size`. No author, no URLs, no mimeType.
  - Checked `acli jira workitem attachment --help` before assuming a download command existed: only `list` and `delete` subcommands exist. **No content-download subcommand in ACLI.** To get actual file bytes, the `content` URL from the `view --fields attachment` response would need to be fetched via REST/curl with Basic Auth, same credentials as the REST fallback path -- not yet tried this session.
  - `attachment list --key ...` follows the same `--key`-as-flag convention as `comment list`, not `view`'s positional-key convention -- consistent with the previously logged finding that flag shape isn't uniform across `workitem` subcommands.
  - Exit-code/output-capture quirk again present on every call, including a case where a call's completion had to be re-verified by checking the log file directly after a session interruption -- file was already correctly populated (152 bytes, valid JSON) despite the interruption, reinforcing that the file write completes independently of whatever caused the interruption/exit-code noise.
- **Result:** worked for metadata (both paths). Content download is a real, confirmed gap -- not attempted.
- **Friction:**
  - Two different ACLI paths return two different shapes for the same data (full object via `view --fields attachment` vs. trimmed `id`/`name`/`size` via `attachment list`) -- worth knowing which one to reach for depending on whether you need the download URL/author or just a quick listing.
  - No native ACLI way to download attachment content -- would require falling back to REST/curl for that one operation even if ACLI is otherwise the primary method for everything else on the same issue.
- **Would reuse as-is?** Yes, for metadata. Content download needs its own dedicated test (REST call against the `content` URL) before SKILL.md can claim attachments are fully covered -- currently only listing/metadata is confirmed, not retrieval of the actual file.
