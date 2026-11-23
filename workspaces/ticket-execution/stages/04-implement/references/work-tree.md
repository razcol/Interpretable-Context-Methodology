# Work tree

`<root>`, `<branch>` and `<path>` come from `plan.md`. `<ws>` is the workspace folder `../../../shared/tools.md` names. `<base>` is the plan's `base` line (the row's Base, from `intake.md`). Run git outside the sandbox when the root is outside this workspace.

## Claim

Other runs may edit the same repo at the same time. Before any `switch` or `worktree add`, claim the work tree and the branch for this run (`../../../shared/tools.md` "run_claim.py"):

```bash
python3 <ws>/../../_core/data-root/run_claim.py target --ws ticket-execution --key <RUN> --path <work tree> --root <root> --branch <branch>
```

`<work tree>` is `<root>` for the main tree, or the worktree `<path>`. Exit 3 on the main tree means another run is editing it: use a worktree as the row or "main tree" in `../../../shared/repo-rows.md` says, claim that path, and say so in the record. Exit 3 on a worktree path or on the branch: stop and return the run it names. Never edit a work tree this run has not claimed.

## Branch in the main tree

Only when `git -C <root> status --short` is empty and this run holds the claim on `<root>`.

```bash
git -C <root> fetch origin
git -C <root> switch -c <branch> origin/<base>  # new branch
git -C <root> switch <branch>                   # existing branch
```

If the tree is dirty or the current branch has unpushed commits (`git -C <root> log origin/<current>..HEAD`), stop and use a worktree instead. Say so in the record.

## Worktree

```bash
git -C <root> fetch origin
git -C <root> worktree add -b <branch> <path> origin/<base>  # new branch
git -C <root> worktree add <path> <branch>                  # existing branch, not checked out elsewhere
```

When `git worktree list` already shows `<path>` on `<branch>`, reuse it.

When the row's "Notes" line names the command that makes this repo's worktree, use that command instead of `git worktree add` (with the same path, branch and base).

Only when `<path>` is inside the root (`<root>/.worktrees/<RUN>`), make sure git ignores that folder, once:

```bash
git -C <root> check-ignore -q .worktrees/x || printf '.worktrees/\n' >> <root>/.git/info/exclude
```

A worktree outside the root (a sibling folder such as `<root>-<KEY>`) needs no exclude line. Do not touch `.git/info/exclude` then.

A fresh worktree has no `node_modules` and no `.env`. Stage 05 handles both through `dev_server.py up`. Do not install here.

## Lint

Use the command in `<data-root>/workspaces/ticket-execution/repos.md` "Lint" for this root, from `code/`, and the repo's lint line under "Notes". Do not search the repo for another eslint or prettier setup. A command of `none` follows `../../../shared/repo-rows.md` "Lint".

When `node_modules` is missing in a fresh worktree, lint runs in stage 05 after the install. Record "lint deferred to 05", and report the Lint audit row as `deferred`, not pass.

## Record

`<runs>/<RUN>/04-implement/implement-record.md`:

```markdown
# <KEY> implement

version: 1

- branch: <name> (created from origin/<base> <hash> | existing at <hash>)
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
- diff vs origin/<base>: before <+a/-b> after <+c/-d>
- smaller option rejected: <one line and the reason, on a simplify, reduce or remove pass; otherwise "n/a">
- added surface: <item: removed | kept: reason, one per line; "none"; or "n/a" when not a simplify, reduce or remove pass>

## Changes
- <date> implement: <one line>
- <date> change: <your text, one line>
```
