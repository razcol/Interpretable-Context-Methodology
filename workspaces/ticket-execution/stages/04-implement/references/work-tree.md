# Work tree

`<root>`, `<branch>` and `<path>` come from `plan.md`. Run git outside the sandbox when the root is outside this workspace.

## Branch in the main tree

Only when `git -C <root> status --short` is empty.

```bash
git -C <root> fetch origin
git -C <root> switch -c <branch> origin/dev     # new branch
git -C <root> switch <branch>                   # existing branch
```

If the tree is dirty or the current branch has unpushed commits (`git -C <root> log origin/<current>..HEAD`), stop and use a worktree instead. Say so in the record.

## Worktree

```bash
git -C <root> fetch origin
git -C <root> worktree add -b <branch> <path> origin/dev    # new branch
git -C <root> worktree add <path> <branch>                  # existing branch, not checked out elsewhere
```

When `git worktree list` already shows `<path>` on `<branch>`, reuse it.

Only when `<path>` is inside the root (`<root>/.worktrees/<KEY>`), make sure git ignores that folder, once:

```bash
git -C <root> check-ignore -q .worktrees/x || printf '.worktrees/\n' >> <root>/.git/info/exclude
```

A sibling-folder worktree (`<root>-<KEY>`) needs no exclude line. Do not touch `.git/info/exclude` then.

A fresh worktree has no `node_modules` and no `.env`. Stage 05 handles both through `dev_server.py up`. Do not install here.

## Lint

Use the command in `targets/repos.md` "Lint" for this root, from `code/`. Do not search the repo for another eslint or prettier setup.

When `node_modules` is missing in a fresh worktree, lint runs in stage 05 after the install. Record "lint deferred to 05", and report the Lint audit row as `deferred`, not pass.

## Record

`output/<KEY>/implement-record.md`:

```markdown
# <KEY> implement

version: 1

- branch: <name> (created from origin/dev <hash> | existing at <hash>)
- work tree: <main tree at root | worktree path>
- app root: <path>/code
- before: <clean | dirty files that were there before, untouched>

## Files changed
- `<path>`: <one line>

## Deviations
<Changes outside the plan, with the reason. Or none.>

## Lint
<command and result, or "deferred to 05">

## Change
- goal: <one line from the change text, or "not a change pass">
- diff vs origin/dev: before <+a/-b> after <+c/-d>
- smaller option rejected: <one line and the reason, on a simplify, reduce or remove pass; otherwise "n/a">
- added surface: <item: removed | kept: reason, one per line; "none"; or "n/a" when not a simplify, reduce or remove pass>

## Changes
- <date> implement: <one line>
- <date> change: <your text, one line>
```
