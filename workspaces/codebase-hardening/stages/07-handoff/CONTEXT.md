# Stage 07: Handoff

Write the project's agent guide and the follow-up plan, after verification has passed.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Previous stage | `../06-verify/output/verification-report.md` | "Verdict", "Rule Results", "Gaps" | Only verified rules are listed as enforced |
| Earlier stage | `../04-enforcement-design/output/enforcement-plan.md` | "Coverage Matrix" and "Rules" | Rationale and messages |
| Earlier stage | `../04-enforcement-design/output/deferred-rules.md` | Full file | The follow-up plan |
| Earlier stage | `../05-implement/output/change-log.md` | "Entrypoint" and "Protected Files" | Check command and protected list |
| Shared | `../../shared/preferences.md` | "Check Command" | The command to state in the guide |
| Reference | `references/handoff-formats.md` | Full file | Shape of both documents |

## Process

1. Read the verdict. Stop unless it is PASS.
2. Write `agent-guide.md` from READY rules that the report shows as caught. Use each rule's own rationale and message.
3. List DOCS-ONLY and DEFERRED rules under "Review manually" and "Known gaps".
4. Write `followup-plan.md` from the deferred entries, in cleanup order.
5. Run the audit.
6. Tell the user both file paths. Offer, but do not perform, copying the guide into the branch.

## Audit

| Check | Pass Condition |
|-------|---------------|
| Verified only | Every enforced entry has a caught row in the verification report |
| No false claims | No DEFERRED or DOCS-ONLY rule is described as enforced |
| Complete follow-up | Every DEFERRED rule appears in `followup-plan.md` |
| Command match | The check command in the guide equals the one in preferences |
| Size | `agent-guide.md` is under 120 lines |

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Agent guide | `output/agent-guide.md` | Sections listed in `references/handoff-formats.md` |
| Follow-up plan | `output/followup-plan.md` | Sections listed in `references/handoff-formats.md` |
