# Repo rows

How every stage reads `<data-root>/workspaces/ticket-execution/repos.md`. That table is your data: one row per repo, with how that repo works. This file holds only the generic rules. A repo's own rules are its row and its lines under "Notes" in the table. When a note and a rule here differ, the note wins for that repo.

## Columns

| Column | Meaning | Read by |
|--------|---------|---------|
| Key | Jira project key. Two rows may share a key (one project, two roots) | 01 |
| Repo | Short name. The "Lint", "Test logins" and "Notes" sections use it | All |
| Root | Absolute path of the repo's main checkout | 01 |
| Branch | Branch name pattern | 03 |
| Work tree | `main tree`, or where the worktree goes | 03, 04 |
| Commit subject | Subject pattern | 07 |
| Base | The branch new work starts from and every diff is measured against, as `origin/<base>` | 01 copies it into `intake.md`; 02 to 06 |
| PR target | The branch the PR goes into | 06 message, 07 |
| PR link | The create-PR link, with `<branch>` where the branch name goes, or `none` | 07 |
| Test route | A page on the dev server where CMS sections under work are placed, or `none yet` | 03, 06 |

Patterns fill in `<id>` (the ticket number), `<kebab>`, `<Sentence>` (from plan "Change", one line), `<root>`, `<branch>`, `<KEY>` (the full ticket key), and `<RUN>` (the run id).

## Rules

- Stage 01 resolves the key to one row. When more than one row has the key, pick one only as that key's line under "Notes" says. Otherwise stop and ask which root.
- A key not in the table: stop and ask for the root and the other columns, then add the row.
- `<kebab>` is three to six English words from the summary, lowercase, hyphens. A bare ticket key (`<KEY>`) is not a branch name. When the run id is `<KEY>--<tail>`, append `--<tail>` to the branch name built from the row pattern.
- "main tree" means the branch is checked out in the root folder. A labeled run (`as <label>`) always uses a worktree. An unlabeled run uses a worktree instead when the root has uncommitted work, is on a branch with unpushed commits, or is claimed by another run (`stages/04-implement/references/work-tree.md` "Claim"). Worktrees go where the row says, or `<root>/.worktrees/<RUN>` when it says main tree. When the run id is `<KEY>--<tail>`, append `--<tail>` to the last path component unless it already ends with `--<tail>` (for example when formed from `<branch>` or `<RUN>`).
- `<base>` is the run's `Base` from the brief, or the row's Base when none was passed. Stage 01 writes it into `intake.md`, stage 03 copies it into `plan.md`, and stages 04 to 07 take it from `plan.md`. A record without a `base:` line (an older run) means the row's Base.
- Stage 06 adds a test route to the row the first time you give one.
- PR target and PR link: when the run's `<base>` equals the row's Base, the PR target and PR link stay the row's (replacing `<branch>` with the branch name, URL-encoded, except that `/` stays as `/`). When the run's `<base>` is another branch, the PR target is the run's `<base>`, and the link's `dest=` value or compare base is replaced with that branch; a link containing neither form has no URL and stage 07 reports the pushed branch and the run's `<base>` instead. A row whose PR link is `none` has no link: stage 07 reports the pushed branch and its PR target instead.
- A line under "Notes" for the run's key or repo applies to every stage that reads the row.

## Lint

The command in the table's "Lint" for the run's repo, from the app folder, on the changed files only. Do not search for another config. A repo whose command is `none` has no lint step: the record's "Lint" says `none for this repo`, and the Lint audit row reads `n/a`.

## Test logins

A repo in the table's "Test logins" has pages behind a login on the local dev server. Stages 05 and 06 sign in with the row's steps file and the secrets file the table names (mode 600, outside every repo). Agents never open, print or copy that file, and never put its values in a prompt, a record or chat; `interact.js --secrets-file` reads it.

- Session `sessionStorage` means the sign-in and the page check run in one tab: one `interact.js --fresh-context` call with the steps file first, then the check (`stages/05-verify/references/verify-steps.md` "Pages behind a login").
- Form submits: `yes` means the dev backend is a test one and stage 05 may send forms; `no` means every row that sends a form is NOT VERIFIED and the browser stays closed for it; `ask` means the orchestrator asks once before stage 05 and writes the answer into the row. When the answer is `no` and every checklist row sends a form, stage 05 is skipped.
- Check that the keys exist with `grep -cE '^(KEY_A|KEY_B)=' <secrets file>`. It prints a count, never the values.
