# Stage 06: Handoff

version: 1

Hand you the work ready to review: the app running on the changed code, the exact local URLs, what to look at on each, and the one word that releases it. Then stop. Nothing is committed or pushed.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 05 | `../05-verify/output/<KEY>/verify-report.md` | Full file | Results, evidence, what was not verified |
| Stage 05 | `../05-verify/output/<KEY>/dev-server.json` | Full file | Port, app root, dev artifacts |
| Stage 04 | `../04-implement/output/<KEY>/implement-record.md` | "branch", "work tree", "app root", "Files changed" | What changed and where |
| Stage 03 | `../03-plan/output/<KEY>/plan.md` | "Review URLs", "Acceptance checklist" | Where to look and what for |
| Message | `references/handoff-message.md` | Full file | URL rules, message and `handoff.md` shape |
| Tools | `../../shared/tools.md` | "dev_server.py", "review_urls.py", "Writing records" | Server check, changed files to routes |
| Repos | `../../targets/repos.md` | The root's row, and its "Test logins" row | Test route, Bitbucket slug, sign-in |
| Browser | `../../../../_core/skills/browser-cdp/SKILL.md` | "Which script to run", "Interaction steps" | The fresh request |
| Sign-in | `../05-verify/references/verify-steps.md` | "Pages behind a login" | The one call for a page behind a login |

## Process

0. When the assignment says the checklist cannot be verified on this backend (submit not allowed), skip steps 1 to 4 and continue at step 5. The not-ready line gives that reason. Do not open a browser.
1. Confirm the server: `dev_server.py status --app-root <app root>`, unsandboxed (`required_permissions: all`). A sandboxed status that says "not answering" is not a reason to restart. When an unsandboxed status says no match answers, run `up` again (background, as in `shared/tools.md`) with the same state file. Exit 0 from `up` means the starter returned. It is not a later check.
2. Run `review_urls.py` with the server's port and the repo's test route. For NSS the review page is `/changeAccount` (see `targets/repos.md`). Do not use `/homepage`; it only shows a loading spinner.
3. When verify already has a screenshot of the review page, the server was not restarted, and the working tree is unchanged since verify, reuse that screenshot. Do not sign in again. Otherwise request the first review URL in a fresh browser context: `node <browser-cdp>/scripts/navigate.js --fresh-context --url <url>` (start the browser first with `browser.js start --profile <key>-handoff --port 9340`, and stop it after). `--port` belongs on `browser.js` only. For a root in "Test logins", use the single sign-in call from verify-steps "Pages behind a login", with `goto` to the first URL and a screenshot, and only when this step is not reusing verify's shot. On a root whose Session in `targets/repos.md` "Test logins" is `sessionStorage`, do not run `navigate.js --fresh-context`, `screenshot.js` or `capture.js` on the review URL. If one ran anyway, ignore what it returned. Record what came back: the acceptance screen, a login page, or no answer. Keep a URL only when that screen shows the change. Drop `review_urls.py` hits that do not render it. A status under 500 does not keep a URL.
4. Collect the diff summary: `git -C <work tree> status --short` and `git -C <work tree> diff --stat origin/dev`, leaving out dev artifacts and anything in `shared/git-rules.md` "Never staged".
5. Write `handoff.md` as `references/handoff-message.md` says. Its first line is `version: 1`. When the fresh request did not show the acceptance screen, or verify was skipped because submits are not allowed, use the not-ready line. When no page is known, say so in the message. Do not stop to ask. Copy stage 05's listed image differences into the message and `handoff.md` as `references/handoff-message.md` says.
6. Post that message once. Return the path to `handoff.md`. Do not open stage 07. The session that spawned you waits for `approve <KEY>`, `commit <KEY>`, `change <KEY>: ...`, or `stop <KEY>`.

## Checkpoints

| After Step | Agent Presents | Human Decides |
|------------|---------------|---------------|
| 6 | The handoff message | `approve`, `commit`, `change`, or `stop` |

## Audit

| Check | Pass Condition |
|-------|---------------|
| Running | A fresh context returns the acceptance screen on the first URL, directly or right after the root's documented sign-in, or verify's screenshot of that screen is reused because the server was not restarted and the tree is unchanged. When verify was skipped because submits are not allowed, the message says that and does not claim an acceptance screen. The message quotes what came back. Status codes on other routes do not pass this. On a `sessionStorage` root, Running is judged from the signed-in tab of each page and width pair (the call that ran the steps file, then `goto` for that pair) or from verify's reused shot of that pair, not from one tab for every URL. A result from a tab that did not run the steps file is not evidence either way. It is not recorded as a login page, does not trigger the not-ready line, and is not quoted |
| URLs | At least one URL, or the message says plainly that none is known and why |
| Nothing staged | `git diff --cached` empty, no new commit on the branch |
| Honest | FAIL and NOT VERIFIED rows appear in the message before the URLs. A PASS the fresh request did not show is reported as not verified for you. Each image difference stage 05 listed for an image-tied row is in the message before the URLs, as a note. It does not change a PASS, the ready line, or the checklist count. Two image reads that disagree on a model name are not a FAIL and do not block PASS |
| Files | The file list matches `git status` minus dev artifacts |
| No extra sign-in | Verify's screenshot of the review page was reused when the server was not restarted and the working tree was unchanged since verify |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Handoff | `output/<KEY>/handoff.md` | See `references/handoff-message.md` |
