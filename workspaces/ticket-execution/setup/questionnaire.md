# Onboarding Questionnaire

Read this file when the user types `setup`. Ask ALL questions below in one pass, so the user can answer everything in one message. Write the answers into the files listed, then confirm the checks at the end.

Before the questions, run `python3 ../../_core/data-root/data_root.py init` from this workspace folder. It creates your data root (default `~/.config/ai-system`) when it is missing and changes nothing when it is complete. See "Data root" in `_core/CONVENTIONS.md`.

These questions configure the workspace. Per-run facts (the ticket, and which root when a key has two) come with the trigger. The defaults below are already written in the files; setup only changes what you answer differently.

### Q1: Which repos do your Jira keys work in, and how does each one work?
- Files: `<data-root>/workspaces/ticket-execution/repos.md` (one row per repo, its "Lint", "Notes" and "Test logins"; when it does not exist, start from `targets/repos.example.md`). Columns: `shared/repo-rows.md` "Columns". Never write a repo's facts into a file of this repo.
- Type: free text, one block per repo to add or change: `KEY = root`, then any column you want to set (base, PR target, PR link, work tree, lint, test route, login).
- Default: the rows already in the table stay as they are. For a new row, propose each column and show them before writing:
  - branch, commit subject and work tree: from the root's recent `git log` and `git worktree list`
  - base and PR target: the branch `git -C <root> symbolic-ref --short refs/remotes/origin/HEAD` names, without `origin/`
  - PR link: from `git -C <root> remote get-url origin`. Bitbucket `<workspace>/<slug>`: `https://bitbucket.org/<workspace>/<slug>/pull-requests/new?source=<branch>&dest=<PR target>`. GitHub `<owner>/<repo>`: `https://github.com/<owner>/<repo>/compare/<PR target>...<branch>?expand=1`. Any other host, or no remote: `none`. Fill in everything except `<branch>`, which stage 07 fills
  - lint: the repo's own lint script or local `eslint` binary, or `none`
  - test route: `none yet`; login: no "Test logins" row unless you give the login path, the steps and the secret key names (never the values)
- A key with two roots: write both rows and a line under "Notes" that says which ticket text picks which root.

### Q2: Which local page shows CMS sections under work, per repo?
- Files: `<data-root>/workspaces/ticket-execution/repos.md` (Test route column; when it does not exist, start from `targets/repos.example.md`)
- Type: free text, `repo = /path/` per line
- Default: the routes already in the table; "none yet" for a new row. When a section has no page, the handoff says so and does not stop to ask.

### Q3: Which Jira site?
- Files: `tools/intake.py` (`JIRA_SITE`), `stages/01-intake/references/intake-steps.md`
- Type: free text, a host name
- Default: `switchil.atlassian.net`

### Q4: Where is your Jira env file for attachment downloads?
- Files: `shared/tools.md`, `stages/01-intake/references/intake-steps.md`
- Type: free text, a path you create yourself with `JIRA_EMAIL=` and `JIRA_API_TOKEN=` lines, `chmod 600`. Do not paste the token into chat.
- Default: `~/.config/jira/jira.env`. Without it, the run goes on and lists the images it could not download.

---

## After Onboarding

Check, and report each result:

1. `acli jira auth status` says Authenticated (full network). If not, follow the jira-research skill.
2. The env file from Q4 exists (do not open it): `test -f <path> && echo present`.
3. `python3 tools/test_tools.py` passes.
4. browser-cdp is installed: `node ../../_core/skills/browser-cdp/scripts/browser.js status` (from this workspace folder) runs.
5. Every row in `<data-root>/workspaces/ticket-execution/repos.md` has each column filled (no `<...>` left), and nothing about a repo was written into this repo.

Then tell the user to start with `start <Jira URL>`.
