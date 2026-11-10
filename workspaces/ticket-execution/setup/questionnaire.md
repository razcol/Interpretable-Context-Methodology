# Onboarding Questionnaire

Read this file when the user types `setup`. Ask ALL questions below in one pass, so the user can answer everything in one message. Write the answers into the files listed, then confirm the checks at the end.

These questions configure the workspace. Per-run facts (the ticket, which `MAIN` site) come with the trigger. The defaults below are already written in the files; setup only changes what you answer differently.

### Q1: Where are your repos, by Jira project key?
- Files: `targets/repos.md` (table)
- Type: free text, `KEY = path` per line
- Default: `LUX = /home/dev/colmobil-luxury-trade`, `OND = /home/dev/ora-next`, `NSS = /home/dev/self-service-cfs/self-service-cfs-next`, `MAIN = /home/dev/jaecoo-next and /home/dev/colmobilnext`
- Derived: the Bitbucket slug is the folder name; the branch, commit and work tree columns are read from each repo's recent `git log` and `git worktree list`.

### Q2: Which local page shows CMS sections under work, per repo?
- Files: `targets/repos.md` (Test route column)
- Type: free text, `repo = /path/` per line
- Default: `ora = /model/ora-05-raz-test/`, others "none yet". When a section has no page, the handoff says so and does not stop to ask.

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
4. browser-cdp is installed: `node /home/dev/ai-system/_core/skills/browser-cdp/scripts/browser.js status` runs.

Then tell the user to start with `start <Jira URL>`.
