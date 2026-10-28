# Codebase Hardening

Turn a project's observed conventions into enforced ones, in seven reviewable stages.

## Task Routing

| Task Type | Go To | Description |
|-----------|-------|-------------|
| New target repo | `stages/01-recon/CONTEXT.md` | Profile the repo: stack, tooling, CI, state |
| Measure conventions | `stages/02-measure/CONTEXT.md` | Run probes and get validated, size-capped reports |
| Choose the rules | `stages/03-synthesize/CONTEXT.md` | Build candidates from reports. The ratifier decides. |
| Design enforcement | `stages/04-enforcement-design/CONTEXT.md` | Pick mechanisms, count violations, sort READY and DEFERRED |
| Build the gates | `stages/05-implement/CONTEXT.md` | Implement READY rules on a branch in a worktree |
| Test the gates | `stages/06-verify/CONTEXT.md` | A fresh context tries to break every rule |
| Hand off | `stages/07-handoff/CONTEXT.md` | Write the agent guide and the follow-up plan |
| Enforce a cleaned-up rule | `stages/04-enforcement-design/CONTEXT.md` | Follow-up pass for one deferred rule |

## Shared Resources

| Resource | Location | Contains |
|----------|----------|----------|
| Playbooks | `playbooks/CONTEXT.md` | Core probes and per-stack recon, probes, enforcement, implementation |
| Preferences | `shared/preferences.md` | Primary stack, ratifier, branch prefix, check command, allowed dev tools |
| Probe report schema | `shared/probe-report-schema.md` | The fixed report shape and size caps |
| Rules manifest schema | `shared/rules-manifest-schema.md` | Candidate and rule blocks, status rules |
| Enforcement ladder | `shared/enforcement-ladder.md` | Five levels from by-construction to docs-only |
| Tamper protection | `shared/tamper-protection.md` | Bypass list, protected files, integrity check |
| Deferral policy | `shared/deferral-policy.md` | READY versus DEFERRED, the user's choices |
| Implementation rules | `shared/implementation-rules.md` | Worktree, branch, allowed paths, fixtures, change log |
| Dispatch | `shared/dispatch.md` | The only harness-specific notes: serial fallback, subagents, hooks |
| Scripts reference | `shared/scripts-reference.md` | Usage of `scripts/measure.mjs` and `scripts/probe-runner.mjs` |
| Prerequisites | `shared/prerequisites.md` | Required and optional tools |
