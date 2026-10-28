# Next.js Enforcement Recipes

Starting points for mapping a ratified convention to a mechanism and a dry run. These are written from documentation and are not yet run against a project. Before using one, check the installed versions (`next`, `eslint`, plugins) and adjust.

## Rule To Mechanism

| Convention | Mechanism | Ladder |
|------------|-----------|--------|
| Ban a styling library | ESLint `no-restricted-imports` for the package, plus the dependency deny-list check | 2 |
| Require one styling approach for new files | Layout test on component folders (style file present), plus import ban for the others | 3 |
| Use `next/image` and `next/link` | `eslint-config-next` rules `@next/next/no-img-element` and `@next/next/no-html-link-for-pages` set to `error` | 2 |
| Limit `use client` to chosen folders | ESLint `no-restricted-syntax` with a directive selector, applied by `overrides` to the forbidden folders; or an ast-grep rule with `files` globs | 2 |
| Server code cannot reach the client | `import 'server-only'` in server modules (build fails on a client import), plus a rule requiring the marker in those folders | 1 |
| Read env vars in one place | `no-restricted-properties` on `process.env` with an override that turns it off for the env module; typed env schema if present | 2 |
| Data access only through one module | `no-restricted-imports` for the database client outside its folder; boundaries plugin or dependency-cruiser for layers | 2 |
| Layer rules (ui cannot import db) | dependency-cruiser `forbidden` rules or `eslint-plugin-boundaries` | 2 |
| File naming and layout | Layout test script in the hardening tools folder | 3 |
| No suppression comments | `@typescript-eslint/ban-ts-comment` and `eslint-comments/no-use` (or `--report-unused-disable-directives` plus a ban rule) | 2 |
| No explicit `any` | `@typescript-eslint/no-explicit-any` as `error` | 2 |
| Strict typing | `tsconfig` flags; dry run with `tsc` flags, see below | 1 |
| Typed internal links | `experimental.typedRoutes` in `next.config` for Next 14 (App Router) | 1 |
| Only approved dependencies | Dependency allow-list and deny-list script against `package.json` | 2 |
| Route file shape (`loading`, `error` per segment) | Layout test over the `app/` tree | 3 |

## Rule Messages

Each ESLint restriction takes a `message`. Write it as the fix: what to use instead, and from where.

## Dry Runs

A dry run counts violations and changes nothing in the target. Keep temporary config outside the repo (a system temp folder).

| Mechanism | Dry run |
|-----------|---------|
| ESLint rule | Write a temp ESLint config holding only that rule. Run ESLint with the project's parser against the source folders and `--format json`. Count messages for that rule. For ESLint 8 use `--no-eslintrc -c <temp config>`. Check the flat-config flags on ESLint 9. |
| ast-grep rule | `ast-grep scan --rule <temp rule file> --json <folders>`. Count matches. |
| dependency-cruiser | `npx depcruise --config <temp config> <folders> --output-type json`. Read `summary.error` and `summary.violations`. |
| Layout test | Run the script in count mode. It prints the number of offending paths. |
| Dependency check | Run the script against `package.json`. Count offending names. |
| Compiler flag (strict, typed routes) | Create a disposable git worktree, apply the flag there, run `tsc --noEmit` or the type-generation step, count the errors. Remove the worktree. |

If a dry run cannot be made to run, the rule's violations are unknown. Unknown is not zero. Do not mark the rule READY. Ask the user.

## Build Interaction

- `next build` runs ESLint unless `eslint.ignoreDuringBuilds` is true. A new error-level rule with existing violations fails the build. That is why such rules stay DEFERRED.
- A rule added at `warn` level changes nothing for existing code, but agents ignore warnings. Prefer `error` for READY rules.

## Limits

- `use client` detection by selector sees the directive only as a top-level statement. Inline `use server` inside a function is a different node.
- Tailwind class-name heuristics in the probes are not a basis for a rule. Confirm with the dependency list and the config file.
- Nothing here checks behavior. A passing check means the shape is right, not that the code is correct.
