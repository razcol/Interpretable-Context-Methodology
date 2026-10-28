# Next.js Recon

What to collect for the project profile. Every fact comes from a command or a file. If a fact cannot be found, write it under Unknowns. Do not guess.

## Repo Facts

| Fact | How |
|------|-----|
| Git top level | `git -C <app> rev-parse --show-toplevel` |
| App root (folder with `package.json` and `next`) | Path the user gave, confirmed by `package.json` listing `next` |
| HEAD sha and branch | `git -C <app> rev-parse HEAD` and `--abbrev-ref HEAD` |
| Tree state | `git -C <app> status --porcelain -- .` (record the paths if not empty) |
| Shallow clone | `git -C <app> rev-parse --is-shallow-repository` |
| Last commit date | `git -C <app> log -1 --format=%ci` |

## Stack Facts

| Fact | How |
|------|-----|
| Next.js, React versions | `dependencies` in `package.json` |
| TypeScript or JavaScript | `tsconfig.json` or `jsconfig.json`; the language-mix probe confirms |
| Package manager | Lockfile: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`. Also the `packageManager` field |
| Router | Existence of `app/`, `src/app/`, `pages/`, `src/pages/`. The router-type probe measures it |
| Styling libraries | Dependency names: tailwindcss, styled-components, @emotion, sass |
| Data layer | Dependency names: prisma, drizzle, mongoose, axios, swr, @tanstack/react-query |
| Node version pin | `.nvmrc`, `.node-version`, `engines` field |

## Tooling Facts

| Fact | How |
|------|-----|
| ESLint config | `.eslintrc*`, `eslint.config.*`, or `eslintConfig` in `package.json`; note `extends` |
| `next.config.*` build flags | Read for `eslint.ignoreDuringBuilds`, `typescript.ignoreBuildErrors`, `experimental.typedRoutes`, `output` |
| TypeScript strictness | `strict`, `noUncheckedIndexedAccess`, `paths` in `tsconfig.json` or `jsconfig.json` |
| Formatter | `.prettierrc*`, `prettier` in `package.json` |
| Tests | `jest.config.*`, `vitest.config.*`, `playwright.config.*`, and the `test` script |
| Local hooks | `.husky/`, `lefthook.yml`, `simple-git-hooks` in `package.json` |
| CI system | `.github/workflows/`, `bitbucket-pipelines.yml`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `.circleci/`, `Jenkinsfile` |
| CODEOWNERS | `CODEOWNERS`, `.github/CODEOWNERS`, `docs/CODEOWNERS` |
| Scripts | The `scripts` object: build, lint, typecheck, test |

CI varies between projects. Record what exists. Do not assume one system.

## Size Facts

Count tracked files by extension: `git -C <app> ls-files | sed 's/.*\.//' | sort | uniq -c | sort -rn | head`. Record the top 8.

## Not Applicable Probes

List probes that cannot apply and why, for example `router-type` is skipped only if no router folder exists at all. This list feeds the skipped-probes file in the measure stage.

## Watch For

- `next build` runs ESLint by default. If `eslint.ignoreDuringBuilds` is true, lint is not part of the build, which changes how a new rule reaches CI.
- A dirty working tree is allowed for recon and measure, but it must be recorded. The implement stage never works in a dirty tree.
- Monorepos: the app root may be a sub-folder. Measure the app root, not the git top level.
