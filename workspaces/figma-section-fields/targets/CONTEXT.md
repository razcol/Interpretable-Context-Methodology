# Targets

Which Next.js repo receives the section.

## Routing

| Need | Go To |
|------|-------|
| Repo roots, default repo, test routes, Figma token file | `<data-root>/workspaces/figma-section-fields/repos.md` (your data: one row per repo; example in `repos.example.md`) |
| Repo structure for this run | `../skills/next-section-repo/SKILL.md` (`probe_repo.py`) |

## Rules

Generic rules for every row. A repo's own facts are its row in the table, never this repo.

- Each repo has its own WordPress and its own fields. Use only the repo named for the run.
- When a run does not name a repo, use the default the table names.
- A run may name another root of the same repo, such as a git worktree; use that path as the repo for every stage of the run. A fresh worktree has no `.env` or wp-graphql sign-in, so run wp-graphql with `--repo <worktree> --store <the main root's store>` (wp-graphql `references/commands.md`, `--store`).
- A row's test route is `none yet` until stage 05 is given one; stage 05 adds it to the row.
- Repo structure (versions, fragments, theme, line endings) is never written into the table: stage 01 reads it fresh with `probe_repo.py` on every run.
