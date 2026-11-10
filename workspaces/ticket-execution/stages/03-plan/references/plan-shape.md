# plan.md

Stage 04 follows this file as written, including the default on each question. The run does not wait for you to edit it. Keep it short enough to read in two minutes.

```markdown
# <KEY> plan

- ticket: <browse URL>
- root: <root>
- branch: <name>  (new from origin/dev | existing)
- work tree: <main tree | path of the worktree to create or reuse>
- app root: <work tree>/code

## Change
<3 to 6 sentences: what changes for the user, and the approach.>

## Files
- `<path>`: <what changes>
- `<path>` (new): <what it holds>

## Acceptance checklist
| # | Line | Check | Where |
|---|------|-------|-------|
| 1 | <acceptance line> | <screenshot / measure / interact / view source / lint> | <path on the dev server, widths> |

## Review URLs
- `<path>`: <what to look at there>

## Not doing
<Acceptance lines or nearby changes left out, each with a reason. Or none.>

## Risks
<What could break elsewhere, and which URL shows it. Or none.>

## Questions
<Each question, then the default this run will take. Or none.>
```

## Rules

- Check methods map to stage 05. `screenshot` and `measure` (horizontal overflow) take widths. `interact` names the click or input. `view source` is for markup asked in the ticket (heading levels, `alt`, lazy load), read from the server HTML. Lint never checks a line on its own.
- Widths: the ticket's widths, or 1920, 1440 and 375 when it shows desktop and mobile, or 1440 when it shows desktop only.
- Review URLs are paths on the local dev server (no host, no port; stage 06 adds them). A CMS section uses the repo's test route from `targets/repos.md`, or a page named in the ticket. When no page is known, write "none known" and a question whose default is to hand off without a page.
- A page behind a login (self-service) says so, names the login path, and says whether the root has a "Test logins" row in `targets/repos.md` ("no test login yet" when it does not).
- An `interact` row that has to send a form (the click that submits it) says `submits` in Check. Stage 05 sends it only when the root's "Form submits" is `yes`. Otherwise the row is NOT VERIFIED with "submit not allowed" and stage 05 does not open a browser for it.
- Schema or data changes (`prisma/`, WordPress fields) are listed in "Files" and called out in "Risks". The dev server never decides them.
- No time estimates.
