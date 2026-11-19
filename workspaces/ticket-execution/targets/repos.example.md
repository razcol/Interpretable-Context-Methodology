# Repos

> Started from `targets/repos.example.md` in the ai-system repo. The live table is `<data-root>/workspaces/ticket-execution/repos.md` (see "Data root" in `_core/CONVENTIONS.md`), and every stage reads only that file. `setup` copies this example there when it is missing. Fill in each `<...>` in the live table, never in the repo.

Which local repo a Jira key works in, and how that repo names things. Stage 01 resolves the key here. Every later stage reads the run's root from `intake.md`, not from this table.

<What every repo shares: where the app lives, what the dev command runs.> The base branch and the PR target are `<base branch>` unless the row says otherwise. Bitbucket workspace: `<bitbucket workspace>`; the repo slug is the root folder name.

| Key | Repo | Root | Branch | Work tree | Commit subject | Test route |
|-----|------|------|--------|-----------|----------------|------------|
| <KEY> | <repo name> | <absolute repo root> | `<KEY>-<id>-<kebab>` | main tree | `<KEY>-<id> <Sentence>` | none yet |

## Rules

- `<KEY with two roots>` has two roots. Stage 01 picks one only when the ticket names the site (<site names>, a URL on one of them). Otherwise it stops and asks.
- A key not in this table: stop and ask for the root, then add the row here.
- `<kebab>` is three to six English words from the summary, lowercase, hyphens. Bare `OND-32` is not a branch name.
- "main tree" means the branch is checked out in the root folder. Use a worktree instead when the root has uncommitted work or is on a branch with unpushed commits. Worktrees go where the row says, or `<root>/.worktrees/<KEY>` when it says main tree.
- A test route is a page on the dev server where CMS sections under work are placed. Stage 06 adds a route here the first time you give one. For `<KEY>`, the review page is `<review route>`.

## Lint

From `code/`, on the changed files only. Do not search for another config.

| Repo | Command |
|------|---------|
| <repo name> | `<lint command, for example ./node_modules/.bin/eslint <files>>` |

<Repo-specific lint notes, such as files the repo's own config ignores, or delete this line.>

## Test logins

Repos whose pages need a login on the local dev server. Stages 05 and 06 sign in with the steps file and the secrets file `~/.config/ticket-execution/test-logins.env` (mode 600, outside every repo). Agents never open, print or copy that file, and never put its values in a prompt, a record or chat; `interact.js --secrets-file` reads it.

| Repo | Login path | Steps file | Secret keys | Session | Form submits |
|------|-----------|------------|-------------|---------|--------------|
| <repo name> | <login path> | `<data-root>/workspaces/ticket-execution/logins/<repo name>.json` (<what the steps do>) | `<SECRET_KEY_A>`, `<SECRET_KEY_B>` | <cookie, or `sessionStorage`: lost in a new tab> | ask |

- Session `sessionStorage` means the sign-in and the page check run in one tab: one `interact.js --fresh-context` call with the steps file first, then the check (`stages/05-verify/references/verify-steps.md` "Pages behind a login").
- Form submits: `yes` means the dev backend is a test one and stage 05 may send forms; `no` means every row that sends a form is NOT VERIFIED and the browser stays closed for it; `ask` means the orchestrator asks once before stage 05 and writes the answer here. When the answer is `no` and every checklist row sends a form, stage 05 is skipped.
- Check that the keys exist with `grep -cE '^(KEY_A|KEY_B)=' ~/.config/ticket-execution/test-logins.env`. It prints a count, never the values.

## Other repos on this machine

No stable key in past work. Use only when you name them: `<absolute repo root>`, `<absolute repo root>`.
