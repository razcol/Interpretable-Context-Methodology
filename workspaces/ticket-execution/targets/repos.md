# Repos

Which local repo a Jira key works in, and how that repo names things. Stage 01 resolves the key here. Every later stage reads the run's root from `intake.md`, not from this table.

All Next repos keep the app in `code/` (package.json, `app/`, `prisma/`). `npm run dev` runs `loadenv` (writes `code/.env` from AWS), `prisma db pull` and `next dev`. The base branch and the PR target are `dev` unless the row says otherwise. Bitbucket workspace: `colwebteam`; the repo slug is the root folder name.

| Key | Repo | Root | Branch | Work tree | Commit subject | Test route |
|-----|------|------|--------|-----------|----------------|------------|
| LUX | luxury-trade | /home/dev/colmobil-luxury-trade | `LUX-<id>-<kebab>` | main tree | `LUX-<id> <Sentence>` | none yet |
| OND | ora | /home/dev/ora-next | `OND-<id>/<kebab>` | `<root>/.worktrees/OND-<id>` | `OND-<id> <Sentence>.` | /model/ora-05-raz-test/ |
| NSS | self-service | /home/dev/self-service-cfs/self-service-cfs-next | `NSS-<id>-<kebab>` | `<root>-NSS-<id>` (sibling folder) | `NSS-<id> <Sentence>` | `/changeAccount` (the account form; pages need a login, see "Test logins". `/homepage` only shows a loading spinner and is not a review page) |
| MAIN | jaecoo | /home/dev/jaecoo-next | `MAIN-<id>-<kebab>` | main tree | `MAIN-<id>: <Sentence>.` | none yet |
| MAIN | colmobil | /home/dev/colmobilnext | `bugfix/MAIN-<id>-<kebab>` | main tree | `<Sentence> (MAIN-<id>).` | none yet |

## Rules

- `MAIN` has two roots. Stage 01 picks one only when the ticket names the site (Jaecoo, Colmobil, a URL on one of them). Otherwise it stops and asks.
- A key not in this table: stop and ask for the root, then add the row here.
- `<kebab>` is three to six English words from the summary, lowercase, hyphens. Bare `OND-32` is not a branch name.
- "main tree" means the branch is checked out in the root folder. Use a worktree instead when the root has uncommitted work or is on a branch with unpushed commits. Worktrees go where the row says, or `<root>/.worktrees/<KEY>` when it says main tree.
- A test route is a page on the dev server where CMS sections under work are placed. Stage 06 adds a route here the first time you give one. For NSS, the review page is `/changeAccount`.

## Lint

From `code/`, on the changed files only. Do not search for another config.

| Repo | Command |
|------|---------|
| self-service | `./node_modules/.bin/eslint <files>` |
| ora | `./node_modules/.bin/eslint <files>` |
| jaecoo | `./node_modules/.bin/eslint <files>` |
| colmobil | `./node_modules/.bin/eslint <files>` |
| luxury-trade | `npx next lint` (no local `eslint` binary; the script lints the app) |

self-service ignores `app/utils/utilApi.tsx` in `code/eslint.config.mjs` (also `utility.tsx`, `utilityForm.tsx`, `app/interfaces/Interfaces.tsx`, `app/i18n/Config.tsx`, `app/shared/components/SVG/Svg.tsx`). A lint run that reports that file as ignored is done. Do not retry with another config.

## Test logins

Repos whose pages need a login on the local dev server. Stages 05 and 06 sign in with the steps file and the secrets file `~/.config/ticket-execution/test-logins.env` (mode 600, outside every repo). Agents never open, print or copy that file, and never put its values in a prompt, a record or chat; `interact.js --secrets-file` reads it.

| Repo | Login path | Steps file | Secret keys | Session | Form submits |
|------|-----------|------------|-------------|---------|--------------|
| self-service | /login | `targets/logins/self-service.json` (identity, terms, 6-digit OTP) | `NSS_TEST_ID`, `NSS_TEST_OTP` | `sessionStorage`: lost in a new tab | ask |

- Session `sessionStorage` means the sign-in and the page check run in one tab: one `interact.js --fresh-context` call with the steps file first, then the check (`stages/05-verify/references/verify-steps.md` "Pages behind a login").
- Form submits: `yes` means the dev backend is a test one and stage 05 may send forms; `no` means every row that sends a form is NOT VERIFIED and the browser stays closed for it; `ask` means the orchestrator asks once before stage 05 and writes the answer here. When the answer is `no` and every checklist row sends a form, stage 05 is skipped.
- Check that the keys exist with `grep -cE '^(KEY_A|KEY_B)=' ~/.config/ticket-execution/test-logins.env`. It prints a count, never the values.

## Other repos on this machine

No stable key in past work. Use only when you name them: `/home/dev/omoda-next`, `/home/dev/smart-next` (checked out on `master`, has `origin/dev`), `/home/dev/hyundai`, `/home/dev/apicolmobil` (WordPress, PHP, no dev server here).
