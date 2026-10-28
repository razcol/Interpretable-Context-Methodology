# Prerequisites

Tools this workspace needs. Required tools are checked at the start of a run. Optional tools are added to a target repo only if `shared/preferences.md` allows them.

## Node.js (required)

A JavaScript runtime. The workspace scripts and most target projects run on it.

- Install: use the official installer or a version manager such as nvm. Version 18 or newer.
- Verify: `node -v` prints a version of 18 or higher.
- Used by: `scripts/measure.mjs`, `scripts/probe-runner.mjs`, and the target project's own tooling.

## git (required)

Version control. Measurement reads tracked files and history. Implementation uses a branch and a worktree.

- Install: your system package manager, or git-scm.com.
- Verify: `git --version` prints a version, and `git -C <repo> status` works in the target.
- Used by: recon, measure, implement, verify.

## Target project's package manager (required)

Whatever the target repo uses: npm, yarn, or pnpm. Detected during recon from the lockfile.

- Install: npm comes with Node.js. yarn and pnpm come from their own installers or from `corepack enable`.
- Verify: the project's own install command works (for example `npm ci`).
- Used by: implement and verify, to install and run the check command.

## dependency-cruiser (optional)

Checks import graphs against rules, for layer and boundary rules.

- Install: as a dev dependency of the target, pinned to an exact version.
- Verify: `npx depcruise --version`.
- Used by: implement, when a boundary rule needs it.

## eslint-plugin-boundaries (optional)

ESLint rules for which folders may import which.

- Install: as a dev dependency of the target, pinned.
- Verify: it loads when ESLint runs with the plugin enabled.
- Used by: implement, as an alternative to dependency-cruiser.

## ast-grep (optional)

Searches and bans code by syntax structure, in any language.

- Install: as a dev dependency of the target (`@ast-grep/cli`), pinned.
- Verify: `npx ast-grep --version`.
- Used by: dry runs and implement, for syntax rules ESLint cannot express.

## Rules For All Installs

- Exact versions only, no ranges.
- Dev dependencies only. Nothing that changes the application or its bundle.
- Every install is listed in the change log.
