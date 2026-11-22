# Handoff message

The goal: you open the first link and see the change. No setup, no searching for the page, no guessing what changed.

## Ready

Ready only when a fresh browser context shows the acceptance screen at the first URL. Then the first line is `**<KEY> is ready for your review.**`

For a root in `<data-root>/workspaces/ticket-execution/repos.md` "Test logins", ready means the screen came back right after the documented sign-in in that fresh context. Then the first line and the line under it are:

```markdown
**<KEY> is ready for your review after you sign in.**
Sign in at [http://localhost:<port><login path>](http://localhost:<port><login path>) with the test identity (`<ID key>` and `<OTP key>` in `~/.config/ticket-execution/test-logins.env`), then open the link below in that same tab.
```

Add "The session does not carry to a new tab." when the row's Session is `sessionStorage`. Do not print the values.

Otherwise the first line is `**<KEY> is not ready for you to review the change.**` Name the URL and what came back (a login page, a different page, or no answer). One more sentence on why that is not the acceptance screen. Do not say ready. Only the documented sign-in can come before the screen; any other login step does not make it ready.

When verify-report.md says PASS but this fresh request does not show the screen, the checklist line counts that row as not verified for you. On a `sessionStorage` root, the fresh request for each page and width is that pair's signed-in tab or verify's reused shot of that pair. A new tab that did not run the steps file, including one that lands on the login page, does not count as not showing the screen.

Before any URL is posted as live, stage 06 step 1 has run `dev_server.py status` unsandboxed in this stage, even after an idle pause. If the server did not answer and a restart did not bring it back, mark each URL as stopped and use the not-ready line (see "Server stopped" below). A dead URL is never posted as live.

## URLs

In this order, without duplicates, each as `http://localhost:<port><path>`. Keep a URL only when the fresh request shows the change there.

1. The plan's "Review URLs".
2. `urls` from `review_urls.py` that the plan did not list.
3. For `section` and `template` files: the repo's test route, or the page the plan named. When neither exists, say in the message that no page is known. Do not stop to ask.
4. For `dynamic` routes: fill the `[param]` with a real value from the plan, the ticket, or the app (a link on a listing page). When no value is known, show the pattern and say which value is missing.
5. `all-pages` (root layout): the home page, plus one page the plan names.

Drop a mapped route that does not render the change, including a page that only shares a translation or layout file. One sentence may say how many were omitted and why. Do not give each omitted route its own bullet.

Next to each kept URL: what to look at, at which width, and any step that stays on that page (scroll to the section, hover a card, open a modal). When the change only shows on mobile, say "open DevTools device mode at 375" or the width. Do not list logging in beyond the one sign-in line above.

When the fresh request did not show the acceptance screen, the message has that one URL and what it showed. No other routes.

## Message in chat

Post this, filled in. Links clickable. No extra sections. Use the not-ready first line when "Ready" above says so.

```markdown
**<KEY> is ready for your review.** <one sentence: what changed for the user>

<Only when present: **Not passing:** row N <line>: <why>. **Not verified:** row N: <why, and how you can check it>.>

<Only when stage 05 listed image differences: **Image differences (a note, not a failure):** row N, `<image file>`: the image shows number <n>; the screen showed number <m>. <Each other difference verify listed for that row, one clause.>>

Open:
- [http://localhost:<port><path>](http://localhost:<port><path>): <what to look at, width, steps on that page>

Running from `<app root>` on port <port> (<started for this run | your server, reused>). Log: `<log path>`.

Branch `<branch>` in `<work tree>`, nothing staged or committed. Diff in Source Control, or:
<git diff --stat lines, at most 15; then "and N more">

<Only when the plan or intake flagged a conflict between Jira text or comments and a ticket screenshot: **Ticket conflict (a note):** <Jira text or comment says X; the screenshot shows Y>. The change follows <X | Y>. Confirm which is right.>

Checklist: <N> of <M> passed. Report: `<runs>/<KEY>/05-verify/verify-report.md`.
Screenshots, one click: [`evidence.html`](<wslPath>) (Windows: `<wslPath>`; Linux: `<html path>`). Raw files: `<runs>/<KEY>/05-verify/shots/`.

Next:
- `approve <KEY>`: commit, push, and give you the PR link against `<PR target>`
- `change <KEY>: <what>`: I change it, recheck, and hand it back on the same server
- `commit <KEY>`: commit only, no push
- `stop <KEY>`: stop the server I started
```

`<PR target>` is the root's PR target in `<data-root>/workspaces/ticket-execution/repos.md`. When the row's PR link is `none`, the `approve` line reads "commit and push; open the PR into `<PR target>` yourself".

Image differences: copy the differences from `verify-report.md`. Do not open the image again to settle them. Match by number, never by model name. When verify did not record which number was on screen, write "verify did not record which number was shown". Never print the test identity values.

Not ready uses the same rest, with this opening instead of the ready line and the Open list:

```markdown
**<KEY> is not ready for you to review the change.** Opening [http://localhost:<port><path>](http://localhost:<port><path>) shows <what came back>. <why that is not the acceptance screen>

**Not verified:** row N <line>: <why>.

<Only when stage 05 listed image differences: **Image differences (a note, not a failure):** row N, `<image file>`: the image shows number <n>; the screen showed number <m>. <Each other difference verify listed for that row, one clause.>>
```

On a `sessionStorage` root, add to the Not verified line that the session does not carry to a new tab.

## Evidence page

Run `python3 <ws>/tools/evidence_html.py <runs>/<KEY> --key <KEY>` once, after the screenshots exist. It writes `<runs>/<KEY>/06-handoff/evidence.html` with the ticket images and the verify screenshots embedded, so one file opens anywhere with no server and no copied paths, and prints JSON with `html` (Linux path) and `wslPath` (`\\wsl.localhost\<distro>\...`, distro from `WSL_DISTRO_NAME`, default `Ubuntu`). Put both paths in the message next to the raw `shots/` path, as in the Checklist line above. The `wslPath` pastes into the Windows Explorer or browser address bar; the Linux path is for a WSL shell or editor. Copy the paths from the tool's output. Do not type them. When the tool fails, give the raw `shots/` path alone and say in one clause that the page was not built.

## Ticket conflicts

When the plan or intake flags that the Jira text or a comment disagrees with a ticket screenshot (for example a label's casing or a different copy line), do not choose one side without saying so. Add the **Ticket conflict** note to the message and the same note to `handoff.md`: what each says, which one the change followed (the plan's choice), and that you can confirm. Conflicts nobody flagged are not hunted for here, and the note does not change a PASS, the ready line or the checklist count.

## Server stopped

When the dev server does not answer after the restart in stage 06 step 1, the first line is `**<KEY> is not ready for you to review the change.** The dev server on port <port> is stopped and did not restart: <reason from the log>.` List each URL as `http://localhost:<port><path> (stopped, not answering)`, not as a link to open, then the command `cd <app root> && npm run dev`. The `evidence.html` line and the rest of the message stay.

Embed one or two screenshots from `shots/` that show the change best, under the URL list. When the message is not ready, say that the shot is from this run's browser, not from the link.

When the dev server could not start (environment failure in 05), the first line says so with the reason, and the message gives the command that starts it (`cd <app root> && npm run dev`) instead of links. A process that answers while the review screen does not come back is the not-ready line, not this one.

## handoff.md

The same content as the message, plus:

```markdown
version: 1

- handed off: <date time>
- port: <port>, pid: <pid>, started by this run: <yes | no>
- files: <full list from git status, without dev artifacts>
- dev artifacts left out: <list or none>
- schema.prisma: <from dev-server.json "schema">
- server check: <alive | restarted, alive | stopped, not answering> at <date time>
- evidence: <wslPath> (Linux: <html path>) | not built: <why>
- ticket conflicts: <one line each, both sides and the side the change followed | none flagged>
```

Stage 07 compares the tree with "files" before it stages anything.
