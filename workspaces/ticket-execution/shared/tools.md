# Tools

Four scripts in `tools/`. Python 3 standard library only. Each prints one JSON object. `<ws>` is `/home/dev/ai-system/workspaces/ticket-execution`. Tests: `python3 <ws>/tools/test_tools.py`.

## Permissions

The chat is often rooted in the app repo, so the records, the browser and the other repos are outside its sandbox. Ask for these on the first call, not after a failure:

| Command | `required_permissions` |
|---------|------------------------|
| `intake.py` | `full_network` |
| `git fetch`, `git worktree add`, any git that writes in a root outside the chat's folder | `all` |
| `dev_server.py status`, `up` and `down` | `all` (`up` as a background command) |
| browser-cdp `browser.js` and every script that connects to it | `all` |
| `curl` to `localhost` | `all` |
| `npm run lint` or `npx eslint` in an app root | `all` |
| `write_record.py` | `all` (it writes outside the app-repo sandbox) |

`git status`, `git diff` and reads need none. `dev_server.py status` needs `all`: a sandboxed status reports "not answering" when the server is up. Never restart on that result.

## Writing records

Write records with the Write or StrReplace tool. When a write is refused, read the reason. For a security-policy denial, fix what it names and write again with the same tool. For any other refusal, retry once.

When the chat's root is outside this workspace (usually the app repo), the Write tool cannot reach `stages/`. Write the record with `tools/write_record.py` instead:

```bash
python3 <ws>/tools/write_record.py --stage <01..07> --key <KEY> <<'RECORD'
<full record text>
RECORD
```

It is the only shell exception in this section: no other heredoc, `python -c`, `tee`, `cat >` or redirect writes a record. The script writes only the stage's own record under `stages/<n>/output/<KEY>/` and refuses every other path. The record name is fixed per stage (`shared/run-records.md`), the whole file is replaced, and the text must carry the `version:` line in its first five lines. For a small edit, read the current file and pass the full new text. Exit 0 written, 2 refused (unknown stage, bad key, a path outside that folder), 3 empty or no `version:` line.

When the script also refuses, put the record's full content in your return with the path it belongs at; the orchestrator reports it. The orchestrator never runs this script and never writes the record.

## intake.py (stage 01)

```bash
python3 <ws>/tools/intake.py '<KEY or browse URL>' --out <ws>/stages/01-intake/output/<KEY> --env-file ~/.config/jira/jira.env
```

- Reads the item with ACLI (`acli jira workitem view <KEY> --fields '*all' --json`). ACLI needs the network: run with full network access.
- Writes `issue.json`, `ticket.md` and, when `JIRA_EMAIL` and `JIRA_API_TOKEN` are in the env file, `attachments/`. Images in the description and comments link to the downloaded files.
- Custom field names need the same token. Without it they show as `customfield_<id>`.
- Sends credentials only to `switchil.atlassian.net`, and follows a redirect only to `api.media.atlassian.com`.
- Exit 0 done, 2 no key in the argument, 3 ACLI missing, failed or signed out (`acli jira auth status`), 4 no such item or no access.
- Read `attachmentsMissing` and `commentsTruncated` in the JSON. Either one non-empty or true is a gap stage 01 reports.

## dev_server.py (stages 05 and 06)

```bash
python3 <ws>/tools/dev_server.py status --app-root <app root>
python3 <ws>/tools/dev_server.py up --app-root <app root> --state <ws>/stages/05-verify/output/<KEY>/dev-server.json --path <first review path>
python3 <ws>/tools/dev_server.py down --state <ws>/stages/05-verify/output/<KEY>/dev-server.json
```

- `status` and `up` must run unsandboxed (`required_permissions: all`). A sandboxed `status` reports "not answering" falsely. Never restart on that result. Confirm with an unsandboxed `status` before `up`.
- `<app root>` is the work tree's `code/` folder, never the main root when the run uses a worktree.
- `up` reuses a server whose working directory is the app root. A server on port 3000 from another folder is listed under `others` and left alone; `up` takes the next free port.
- On reuse, `up` writes the state file too. When the server is the one this key's earlier `up` started, `startedByUs` stays true. Any other server is recorded with its live pid and `startedByUs: false`, and `down` leaves it running. Do not edit `dev-server.json` by hand. `up` probes `--path` on a reused server until it answers below 500 or `--timeout` runs out, and exits 7 otherwise, like a fresh start. The state file records `listenerPid`, the process on the port, next to `pid`, the npm process group that `down` stops.
- Run `up` as a background shell command (do not block on it), then wait for its JSON. A foreground call that ends can take the server down with it. `up` needs full network access (AWS for `loadenv`, the database for `prisma db pull`) and no sandbox.
- First start in a fresh worktree runs `npm ci` and can take several minutes. First page compile takes about 30 seconds.
- `schema` says whether `prisma db pull` rewrote `prisma/schema.prisma` and whether it was restored. `devArtifacts` lists files the start created (Next 16 writes `AGENTS.md`). Neither is part of the work.
- Exit 0 ok, 2 bad arguments or no free port, 5 install failed, 6 the server exited (read `tail`), 7 no answer before the timeout.
- Exit 0 means the starter returned. `httpStatus` in that JSON is the startup request. A later notice that this command finished is the starter ending. It does not mean the server stopped, and it does not mean a new browser still gets the review screen. Check with `status`, then request the review path again.
- `down` stops only a server `up` started for this key (`startedByUs` true).

## review_urls.py (stage 06)

```bash
python3 <ws>/tools/review_urls.py --app-root <app root> --base origin/dev --port <port> [--test-route <route>]
```

- Changed files are all differences from the merge base with `--base`, committed or not, plus untracked files.
- Follows imports backwards (relative, jsconfig `paths`, `baseUrl`) to `page.*` and `layout.*` under `app/`.
- `kind` per file: `static`, `dynamic` (route keeps `[param]`), `wordpress` (only through the catch-all CMS page), `section` (`components/Sections/<Name>/`), `template` (`components/Templates/<Name>/`), `all-pages` (root layout), `unmapped`.
- `sharedStringsOnly` lists routes reached only through a changed locale file whose changed keys that route does not use. They are not in `urls`. When the script cannot tell, the route stays in `urls`. Each locale file's entry has `changedKeys` (`null` when it cannot tell).
- `urls` are ready to open. `needsAnswer` lists files whose page the code cannot tell: the plan's review URLs, the test route, or you fill those in.
