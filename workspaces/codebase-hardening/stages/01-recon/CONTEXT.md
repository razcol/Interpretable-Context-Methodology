# Stage 01: Recon

Profile the target repository before anything is measured.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| User | (conversation) | Target repo path, and the app root if the repo holds several apps | The per-run target |
| Shared | `../../shared/preferences.md` | "Primary Stack" | Picks the playbook |
| Routing | `../../playbooks/CONTEXT.md` | "What Loads" table, Recon column | Which recon file to load |
| Reference | `references/profile-format.md` | Full file | Exact shape of the profile |
| Shared | `../../shared/prerequisites.md` | "Node.js", "git", and "Target project's package manager" | Confirm required tools exist |

## Process

1. Ask the user for the target repo path. If the repo holds several apps, ask which app root to use.
2. Check prerequisites: `node -v`, `git --version`, and that the path is a git repository.
3. Load the recon file for the Primary Stack from the routing table.
4. Run the recon commands it lists. Record every fact with its source.
5. Decide which probes cannot apply, and why.
6. Write the profile in the exact format. Put gaps under Unknowns. Never guess.
7. Run the audit, then save to output/.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Sections present | Run, Repo, Stack, Tooling, Not Applicable Probes, and Unknowns all exist |
| Sha recorded | The full HEAD sha and the tree state are in Run |
| Sourced facts | Every fact names the command or file it came from |
| No secrets | No token, key, or environment value was copied from any file |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Project profile | `output/project-profile.md` | Markdown with the sections defined in `references/profile-format.md` |
