# Stage 02: Research

version: 1

Find where the asked behavior lives in the repo, what live WordPress has for it, how a sibling repo already does it, and what earlier commits decided. Read only: no edits in any repo. The wp-graphql commands are allowed. They do not edit a repo.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `<runs>/<RUN>/01-intake/intake.md` | Full file | What is asked, root, acceptance |
| Stage 01 | `<runs>/<RUN>/01-intake/attachments/` | Images named in "Images" | What it should look like |
| Rules | `references/research-rules.md` | Full file | Where to look, when and how to check live WordPress, what to leave out, `research.md` shape |
| Repos | `<data-root>/workspaces/ticket-execution/repos.md` | "Notes" | Siblings |
| Git | `../../shared/git-rules.md` | "Allowed per stage" | Read-only git, plus the wp-graphql commands the rules name |
| Repo | `<root>` from `intake.md` | Files the search finds | The code |
| Live schema | `../../../../_core/skills/wp-graphql/SKILL.md` | "Which command", "Output", "Secrets" | Live ACF facts for each `wp: yes` line. A `.gql` file is what the code selects, not what WordPress has |
| Records | `../../shared/tools.md` | "Permissions", "Writing records" | The permission the wp-graphql commands need; how to write this stage's record when the chat is rooted in the app repo |

## Process

1. The record's first line is `version: 1`. Run `git -C <root> fetch origin` and note the current branch and whether the tree is dirty (`git status --short`).
2. Locate each acceptance line in code: the route, the component, the data (fragment, API, Prisma). Follow `references/research-rules.md` "Where to look".
3. When the same feature exists in a sibling repo, read how it is built there. Siblings and exclusions are in the rules file.
4. Mark each acceptance line `wp: yes` or `wp: no` as `references/research-rules.md` "Live WordPress" says. For each `wp: yes` line, run the command that section names on the intake root, and on the sibling root when step 3 cites one, with `required_permissions: all`. Write each result as that line's live block. A `.gql` file, a sibling's fragment or an earlier record never settles what WordPress has.
5. Read `git log` for the files you found, enough to learn earlier decisions and the repo's naming.
6. Write `research.md`. Return its path and each audit row. Do not open stage 03.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Coverage | Every acceptance line in `intake.md` has at least one file path, or is listed under "Not found in code". Every line reads `wp: yes` or `wp: no` with a reason |
| Live | Every `wp: yes` line has a live block for each repo it makes a claim about, run with `required_permissions: all`. Names under `present` and `absent` come from that call's `summary` or `tree`. No "has not", "missing", "does not exist" or "create" about WordPress unless an `ok: true` block on that repo lists the name under `absent`. `pass` when every block is `ok: true`. `pass (no wp lines)` when every line is `wp: no`. `unconfirmed: <line numbers>` when each failed block is under "Unconfirmed live" with its code after the retries the rules allow; this is not a failed audit, and stages 03 and 04 carry it. `fail` when a `wp: yes` line has no command, a call ran sandboxed, or a WordPress claim has no block |
| Paths | Every path in `research.md` exists in the tree it names |
| Read only | `git status` of the root is the same as in step 1 |
| Scope | Nothing in `research.md` that no acceptance line needs |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Research | `<runs>/<RUN>/02-research/research.md` | See `references/research-rules.md` "research.md" |
