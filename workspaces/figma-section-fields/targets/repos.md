# Repos

The section repos this workspace writes into. Repo structure (versions, fragments, theme, line endings) is never written here: stage 01 reads it fresh with `probe_repo.py` on every run.

| Repo | Root | Test route (stage 05) |
|------|------|-----------------------|
| ora | /home/dev/ora-next | /model/ora-05-raz-test/ |
| smart | /home/dev/smart-next | none yet |
| jaecoo | /home/dev/jaecoo-next | none yet |
| luxury-trade | /home/dev/colmobil-luxury-trade | none yet |
| omoda | /home/dev/omoda-next | none yet |

When a run does not name a repo, use ora.

Each repo has its own WordPress and its own fields. Use only the repo named for the run. A run may name another root of the same repo, such as a git worktree; use that path as the repo for every stage of the run. A fresh worktree has no `.env` or wp-graphql sign-in, so run wp-graphql with `--repo <worktree> --store <the main root's store>` (wp-graphql `references/commands.md`, `--store`).
