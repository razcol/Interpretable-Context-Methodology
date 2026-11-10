# Stage 02: Research

version: 1

Find where the asked behavior lives in the repo, how a sibling repo already does it, and what earlier commits decided. Read only.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Stage 01 | `../01-intake/output/<KEY>/intake.md` | Full file | What is asked, root, acceptance |
| Stage 01 | `../01-intake/output/<KEY>/attachments/` | Images named in "Images" | What it should look like |
| Rules | `references/research-rules.md` | Full file | Where to look, what to leave out, `research.md` shape |
| Git | `../../shared/git-rules.md` | "Allowed per stage" | Read-only commands |
| Repo | `<root>` from `intake.md` | Files the search finds | The code |
| Records | `../../shared/tools.md` | "Writing records" | How to write this stage's record when the chat is rooted in the app repo |

## Process

1. The record's first line is `version: 1`. Run `git -C <root> fetch origin` and note the current branch and whether the tree is dirty (`git status --short`).
2. Locate each acceptance line in code: the route, the component, the data (fragment, API, Prisma). Follow `references/research-rules.md` "Where to look".
3. When the same feature exists in a sibling repo, read how it is built there. Siblings and exclusions are in the rules file.
4. Read `git log` for the files you found, enough to learn earlier decisions and the repo's naming.
5. Write `research.md`. Return its path and each audit row. Do not open stage 03.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Coverage | Every acceptance line in `intake.md` has at least one file path, or is listed under "Not found" |
| Paths | Every path in `research.md` exists in the tree it names |
| Read only | `git status` of the root is the same as in step 1 |
| Scope | Nothing in `research.md` that no acceptance line needs |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Research | `output/<KEY>/research.md` | See `references/research-rules.md` "research.md" |
