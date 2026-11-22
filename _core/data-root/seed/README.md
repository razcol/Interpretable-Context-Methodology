# ai-system data root

This folder is your own data for ai-system: repo tables, login steps, logs, session briefs and run records. It is a local git repo of its own, so it is your history and your backup. Copy, back up or share it on its own, apart from the ai-system repo.

- `LAYOUT` names the layout version and the folders.
- `.gitignore` keeps env files, secrets, caches and locks out of commits.
- `.gitattributes` lets logs and briefs merge without conflicts.

The rules for this folder live in the ai-system repo, in the "Data root" section of `_core/CONVENTIONS.md`.
