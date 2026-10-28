# Stage 06: Verify

Try to break every gate in a fresh context, and report what gets through.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../05-implement/output/change-log.md` | Full file | Rules, branch, check command, protected files |
| Target repo | The branch named in the change log | Read through a disposable worktree | The code under test |
| Shared | `../../shared/tamper-protection.md` | "Bypass Attempts" | The bypass list |
| Shared | `../../shared/dispatch.md` | "Independent Verification" | Why the context must be fresh |
| Reference | `references/verification-protocol.md` | Full file | Steps, verdict, report shape |

## Process

1. Confirm this session has no memory of implementing. If it does, start a fresh session or worker.
2. Create a disposable worktree from the branch. Install with the lockfile. Confirm the check command passes on it.
3. For each implemented rule, run the violation test and the compliant test.
4. Run each bypass test that the change log says is covered.
5. Remove the disposable worktree. Confirm the user's working tree is unchanged.
6. Write the report with a PASS or FAIL verdict. On FAIL, tell the user to return to Stage 05.
7. Run the audit.

## Audit

| Check | Pass Condition |
|-------|---------------|
| All rules tested | Every rule in the change log has a row in Rule Results |
| All covered bypasses tested | Every covered bypass has a row with its command |
| Evidence recorded | Each result lists the command and exit code |
| Clean exit | The disposable worktree is gone and `git status` matches the start |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Verification report | `output/verification-report.md` | Verdict, Rule Results, Bypass Results, Gaps |
