# Onboarding Questionnaire: Outlook Email Manager

Read this file when the user types "setup". Ask ALL questions below in a single conversational pass.

---

### Q1: Where did you install the bundled outlookctl tool?
- Files: `skills/outlook-automation/SKILL.md`, `skills/outlook-automation/outlookctl-bridge.sh`
- Type: no path to collect -- the workspace runs outlookctl through `skills/outlook-automation/outlookctl-bridge.sh`, which locates everything itself
- Purpose: `outlookctl` depends on `pywin32`/Windows COM, so it must run as a genuine Windows-native process. If this workspace lives under WSL (as it does by default), running `uv`/python directly from the WSL shell does not work at all (`pywin32` has no Linux wheel), and pointing a `powershell.exe`-launched `uv` at a `\\wsl$\...`/`\\wsl.localhost\...` path is unreliable (it can succeed once and then fail on the next identical run, due to WSL UNC access being scoped to the interactive logon session). The bridge script avoids both problems: it mirrors `outlookctl-src/` to a native Windows path (`%LOCALAPPDATA%\outlookctl-bridge`) and runs `uv.exe` from there via `powershell.exe`, decoding output back to UTF-8. This has been verified to pass `doctor` and return live data from Outlook COM across multiple consecutive runs.
- Prerequisite: `uv` must be installed on the **Windows** side (not just inside WSL). If `%USERPROFILE%\.local\bin\uv.exe` does not exist on Windows, install `uv` there first: https://docs.astral.sh/uv/getting-started/installation/. See `../stages/01-triage/references/outlookctl-setup.md` for full install steps.
- If the workspace does NOT live under WSL (i.e. it's already on a native Windows filesystem), the bridge script is unnecessary -- run `outlookctl-src` directly with `uv run --project "<path>" python -m outlookctl.cli <command>` from a native Windows terminal instead.

### Q2: List any VIP senders whose email should always be treated as high priority.
- Placeholder: `{{VIP_SENDER_LIST}}`
- Files: `shared/priority-rubric.md`
- Type: free text (names or email addresses, comma-separated)
- Default: "(none yet -- add names or email addresses here as you notice who matters most)" -- an empty VIP list is normal, not something to remove. You can add senders later by editing `shared/priority-rubric.md` directly, no need to re-run setup.

### Q3: How many of your sent emails should the tone profile setup analyze?
- Type: free text (a number)
- Default: 100
- Purpose: Used as the `--count` value when running tone-profile setup's `outlookctl search --folder sent` step. Not a placeholder in any file -- just remembered for the first `learn my tone` run.

---

## After Onboarding

Tell the user: "Setup is done. Before your first real run, say 'learn my tone' so I can derive your voice profile from your sent email -- this only needs to happen once. After that, say 'process my inbox' anytime to triage unread email and draft replies."

If you have more than one Outlook profile/mailbox configured, outlookctl targets the default profile unless told otherwise. Mention this only if it comes up.

Then scan the entire workspace for any remaining `{{` patterns. If any remain, ask the user for the missing information.
