# Implementation Rules

Stack-neutral rules for changing a target repository. Playbooks add stack details.

## Golden Rules

1. **Work in a worktree.** Create a separate git worktree for the hardening branch. The user's working tree, including uncommitted changes, is never touched.
2. **Change no application code.** Only configuration, tooling, and documentation files change. If a rule seems to need an application change, it is DEFERRED, not implemented.
3. **READY rules only.** Re-run every READY rule's dry run first. Any non-zero count stops the stage and sends it back.
4. **Nothing leaves the machine.** Never push, open a pull request, or merge. The user does that after review.
5. **Fail closed.** Every gate treats a crash, a missing tool, or an empty result as a failure.

## Branch

- Name: `<Branch Prefix from shared/preferences.md><YYYYMMDD>-<short-slug>`
- Follow-up passes use the same pattern with `-followup-<rule-id>` at the end.
- Base: the HEAD recorded in the project profile. If HEAD moved, stop and re-run the dry runs.
- Worktree location: a sibling folder of the repository named `<repo>-harden`, or a system temp folder. Never inside the repository.

## Allowed Changed Paths

| Path | Why |
|------|-----|
| Lint, type, and build configuration files | Rule levels and settings |
| `package.json` and the lockfile | Dev dependencies and the check script only |
| `tools/harden/` | Rules, fixtures, scripts, hash list |
| CI definition | One step that calls the check command |
| CODEOWNERS | Protects the gates |
| Agent guide file (only if the user asks) | Handoff |

Check this list with `git diff --name-only <base>`. Any other path is a defect.

## Hardening Folder

`tools/harden/` holds everything the workspace adds to a target:

```
tools/harden/
  check.mjs          entrypoint, fail closed
  checks/            layout tests and dependency check
  eslint-rules/      custom rules (ladder 4)
  fixtures/<rule-id>/should-fail.* and should-pass.*
  protected.sha256   hashes of protected files
```

## Every Rule Ships Three Things

1. The enforcement itself.
2. A should-fail fixture and a should-pass fixture under `fixtures/<rule-id>/`.
3. A fixture test inside the check command: the should-fail fixture must produce the rule's message, and the should-pass fixture must pass.

## Commits

One commit per logical group: dependencies, each rule or small set of rules, tamper protection, CI. Message format: `harden: <what> (<rule ids>)`. No commit skips hooks.

## Installs

Use the project's package manager with its lockfile. Exact versions. Only tools listed under Allowed Dev Tools in `shared/preferences.md`. Record each one in the change log.

## Change Log Format

The change log is the only input the verify stage gets besides the branch.

| Section | Content |
|---------|---------|
| Branch | Name, base sha, worktree path |
| Entrypoint | The check command and the order of its parts |
| Rules | Table: id, title, mechanism, how to run that rule alone, fixture path, message |
| Installs | Package, exact version, why |
| Protected Files | The full list |
| Verification | Check command, build, and tests results with exit codes |
| Changed Paths | Output of the diff name list |
| Not Implemented | DEFERRED, DOCS-ONLY, and DROPPED rule ids |
