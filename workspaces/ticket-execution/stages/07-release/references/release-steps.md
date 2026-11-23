# Release steps

`<wt>` is the work tree from `handoff.md`. Run git outside the sandbox. Push needs network access.

## Commit

```bash
git -C <wt> add -- <each reviewed file by path>
git -C <wt> diff --cached --name-only      # must equal the reviewed list
git -C <wt> commit -m "<subject>"
git -C <wt> show --stat --format='%h %s' HEAD
```

Never `git add -A`, `git add .` or `git commit -a`. A deleted file is staged with `git add -- <path>` like any other.

Subject: the repo's pattern from `<data-root>/workspaces/ticket-execution/repos.md`, from plan "Change", one line. A bundle plan makes one commit per key with that key's files.

A pre-commit hook that fails: show its output, fix what the change caused, and run the commit again. Never `--no-verify` unless you type it.

## Push (approve only)

```bash
git -C <wt> push -u origin <branch>
```

Rejected because the remote moved: stop and show the message. No force push, no rebase, unless you type it.

## PR link

When the run's `<base>` (from `plan.md`) equals the row's Base, use the row's PR target and PR link with `<branch>` replaced as `../../../shared/repo-rows.md` "Rules" says (URL-encoded; a `/` in the branch stays as `/`). When the run's `<base>` is some other branch, the PR target is `<base>`, and replace the link's `dest=` value or compare base with `<base>`. When the row's PR link is `none`, or when `<base>` differs from the row's Base and the link contains neither `dest=` nor a compare base, there is no link: report the pushed branch and the PR target instead.

## Reply

```markdown
**<KEY> committed and pushed.** `<hash> <subject>`
Create the PR: [<root folder name>: <branch> into <PR target>](<PR link>)
The server is still running on http://localhost:<port>. `stop <KEY>[ on <base>][ as <label>]` stops it.
```

When there is no PR link, the PR line is "Pushed `<branch>` to origin. Open the PR into `<PR target>` there."

On `commit`, the first line says "committed, not pushed" and the PR line is replaced with "`approve <KEY>[ on <base>][ as <label>]` pushes it."

## release-record.md

```markdown
# <KEY> release

- commit: <hash> <subject>
- files: <list>
- pushed: <yes, origin/<branch> | no>
- PR: <link | no PR link for this repo, target <PR target> | not pushed>
- date: <date time>
```
