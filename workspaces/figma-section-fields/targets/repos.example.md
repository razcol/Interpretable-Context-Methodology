# Repos

> Started from `targets/repos.example.md` in the ai-system repo. The live table is `<data-root>/workspaces/figma-section-fields/repos.md` (see "Data root" in `_core/CONVENTIONS.md`), and every stage reads only that file. `setup` copies this example there when it is missing. Fill in each `<...>` in the live table, never in the repo.

The section repos this workspace writes into. Repo structure (versions, fragments, theme, line endings) is never written here: stage 01 reads it fresh with `probe_repo.py` on every run.

| Repo | Root | Test route (stage 05) |
|------|------|-----------------------|
| <repo name> | <absolute repo root> | <test route, or none yet> |

When a run does not name a repo, use <default repo name>.

Each repo has its own WordPress and its own fields. Use only the repo named for the run. A run may name another root of the same repo, such as a git worktree; use that path as the repo for every stage of the run. A fresh worktree has no `.env` or wp-graphql sign-in, so run wp-graphql with `--repo <worktree> --store <the main root's store>` (wp-graphql `references/commands.md`, `--store`).
