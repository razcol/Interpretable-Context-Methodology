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

The row's PR link, with `<branch>` replaced as `../../../shared/repo-rows.md` "Rules" says (URL-encoded; a `/` in the branch stays as `/`). When the row's PR link is `none`, there is no link.

## Reply

```markdown
**<KEY> committed and pushed.** `<hash> <subject>`
Create the PR: [<root folder name>: <branch> into <PR target>](<PR link>)
The server is still running on http://localhost:<port>. `stop <KEY>` stops it.
```

When the row has no PR link, the PR line is "Pushed `<branch>` to origin. Open the PR into `<PR target>` there."

On `commit <KEY>`, the first line says "committed, not pushed" and the PR line is replaced with "`approve <KEY>` pushes it."

## release-record.md

```markdown
# <KEY> release

- commit: <hash> <subject>
- files: <list>
- pushed: <yes, origin/<branch> | no>
- PR: <link | no PR link for this repo, target <PR target> | not pushed>
- date: <date time>
```
