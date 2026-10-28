# Next.js Implementation Notes

How the stack-neutral implementation rules apply to a Next.js project. Written from documentation and not yet run end to end. Verify against the installed versions.

## Where Things Go

| Item | Location in the target |
|------|------------------------|
| ESLint rules and overrides | The project's existing ESLint config, extended in place. Do not add a second config file. |
| Custom ESLint rules (ladder 4) | `tools/harden/eslint-rules/` loaded by a local plugin file |
| ast-grep rules | `tools/harden/sgrules/` and `sgconfig.yml` |
| dependency-cruiser config | `tools/harden/dependency-cruiser.cjs` |
| Layout tests and dependency check | `tools/harden/checks/*.mjs` |
| Fixtures | `tools/harden/fixtures/<rule-id>/should-fail.*` and `should-pass.*` |
| Protected-file hash list | `tools/harden/protected.sha256` |
| Check script | `scripts.check` in `package.json` calling `tools/harden/check.mjs` |

The folder name `tools/harden` comes from `../../shared/implementation-rules.md`. Change it only for a reason recorded in the change log.

## Fixtures Must Not Pollute The App

Fixtures intentionally contain violations. Keep them out of lint, type checks, and the build:

- Exclude `tools/harden/fixtures/**` from the normal ESLint run and from `tsconfig` `include`.
- The check script runs rules against fixtures with explicit file arguments and expects the should-fail files to produce the rule's message.
- Give fixtures a non-route path so Next.js never treats them as pages.

## The Check Command

`check.mjs` runs, in order, and stops with a non-zero exit on the first failure or on any crash:

1. Protected-file integrity check
2. Dependency allow-list and deny-list check
3. ESLint on all tracked source paths with the hardened config
4. Layout tests
5. ast-grep and dependency-cruiser, if used
6. Fixture tests: every should-fail fixture must fail its rule, every should-pass fixture must pass

The script lists its own parts and fails if one is missing. The package script named in `shared/preferences.md` calls it.

## Verifying The Branch

Run from the worktree, after installing with the lockfile (for example `npm ci`):

1. The check command exits 0.
2. The project's build script exits 0. For Next.js this is normally `next build`.
3. The project's test script exits 0, if one exists.
4. `git diff --name-only <base>` lists only allowed paths (configs, `package.json`, the lockfile, `tools/harden/`, CI, CODEOWNERS). No file under the application source folders appears.

## Install Notes

- Add only tools allowed in `shared/preferences.md`, as dev dependencies, with exact versions.
- Check that a new ESLint plugin supports the installed ESLint major version before adding it.
- Do not run `npm install` in the user's working tree. Use the worktree.

## CI

CI varies by project. Add one job or step that runs the check command. Use the CI definition already in the repo and keep the edit small. If there is no CI, record that in the change log and leave the local hook as the only gate, flagged as weak.
