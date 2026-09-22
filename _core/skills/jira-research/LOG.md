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


