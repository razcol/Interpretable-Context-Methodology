# Repos

> Started from `targets/repos.example.md` in the ai-system repo. The live table is `<data-root>/workspaces/ticket-execution/repos.md` (see "Data root" in `_core/CONVENTIONS.md`), and every stage reads only that file. `setup` copies this example there when it is missing, and adds or changes rows when you answer its questions. Fill in each `<...>` in the live table, never in the repo. How each column is read: `workspaces/ticket-execution/shared/repo-rows.md` in the ai-system repo.

Which local repo a Jira key works in, and how that repo works: one row per repo. Stage 01 resolves the key here. Every later stage reads the run's root and base from `intake.md`, and the rest of the row from this table.

<What every repo shares: where the app lives, what the dev command runs, or delete this line.>

| Key | Repo | Root | Branch | Work tree | Commit subject | Base | PR target | PR link | Test route |
|-----|------|------|--------|-----------|----------------|------|-----------|---------|------------|
| <KEY> | <repo name> | <absolute repo root> | `<KEY>-<id>-<kebab>` | <main tree, or the worktree path, for example `<root>/.worktrees/<KEY>`> | `<KEY>-<id> <Sentence>` | `<base branch>` | `<PR target branch>` | `<create-PR link with <branch> in it, or none>` | <test route, or none yet> |

## Notes

Rules that belong to one key or repo. Each adds to the generic rules in `shared/repo-rows.md`.

- <KEY with two roots>: two roots. Pick <repo name> only when the ticket names <site name> or a URL on its site, <other repo name> only when it names <other site name>. Otherwise stop and ask.
- <repo name>: the review page is `<review route>`. Do not use `<route that does not show the change>`.
- <repo name> lint: <files the repo's own config ignores, and when a lint run is done>.
- Siblings: <repos that share one structure, where a feature often exists in one before another>. <Repos to leave out of a cross-repo survey unless you name them.>

## Lint

| Repo | Command |
|------|---------|
| <repo name> | `<lint command, for example ./node_modules/.bin/eslint <files>, or none>` |

## Test logins

Repos whose pages need a login on the local dev server. Secrets file: `<secrets env file, mode 600, outside every repo>`.

| Repo | Login path | Steps file | Secret keys | Session | Form submits |
|------|-----------|------------|-------------|---------|--------------|
| <repo name> | <login path> | `<data-root>/workspaces/ticket-execution/logins/<repo name>.json` (<what the steps do>) | `<SECRET_KEY_A>`, `<SECRET_KEY_B>` | <cookie, or `sessionStorage`: lost in a new tab> | ask |

## Other repos on this machine

No stable key in past work. Use only when you name them: `<absolute repo root>`, `<absolute repo root>`.
