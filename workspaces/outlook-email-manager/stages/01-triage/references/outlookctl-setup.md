# outlookctl Setup Guide

What it is: a local command-line tool that lets the agent read, categorize, and draft email in Classic Outlook on Windows, using the same COM automation interface VBA macros use. No cloud calls, no OAuth, no API keys -- it controls the Outlook session already running on your machine.

This workspace bundles a locally patched copy at `../../skills/outlook-automation/`. The patch adds category support (list/get/set/filter) that the upstream project does not yet have -- see "Local Patch" below.

## Running from WSL

`outlookctl` depends on `pywin32`, which talks to Outlook through Windows COM automation, so it must run as a genuine Windows-native process. If this workspace lives under WSL (as it does by default), two approaches that look plausible do **not** work reliably -- do not use them:

- Running `uv`/python directly from a WSL/Linux shell: `pywin32` has no Linux wheel, so `uv sync` fails immediately. This has been directly confirmed: `uv` reports "pywin32 (v312) only has wheels for the following platforms: win32, win_amd64, win_arm64" and refuses to sync.
- Invoking `powershell.exe` from WSL with `--project` pointed at a `\\wsl$\...` or `\\wsl.localhost\...` UNC path: this is unreliable. A `powershell.exe` process spawned via WSL interop runs in its own logon session, and mapped/UNC access to the WSL 9P share is scoped to the interactive desktop session, not that spawned session -- so this can succeed once and then fail on the next, otherwise identical, invocation ("Project directory does not exist", "network name is no longer available"). Treat a single successful run of this pattern as inconclusive, not as verification.

**The verified, repeatable pattern** is the bridge script at `../../skills/outlook-automation/outlookctl-bridge.sh`. It mirrors `outlookctl-src/` to a native Windows path (`%LOCALAPPDATA%\outlookctl-bridge`) and runs `uv.exe`/python from there via `powershell.exe`, decoding the redirected UTF-16LE output back to UTF-8 and propagating the real exit code. This has been confirmed across multiple consecutive runs of `doctor`, `category list`, and `list --folder inbox` (all returning live data from Outlook COM, `all_passed: true`).

## Prerequisites

- Windows with **Classic Outlook** (not "New Outlook") installed and running, logged into your account
- Python 3.12 or later
- `uv` (Python package manager) installed **on the Windows side** -- not just inside WSL. The installer commonly places it at `%USERPROFILE%\.local\bin\uv.exe`, which does not need to be on Windows `PATH` (the bridge script calls it by full path). Install from https://docs.astral.sh/uv/getting-started/installation/ if `uv.exe` is not already there.

## Install

1. The bundled tool lives at `skills/outlook-automation/outlookctl-src/` inside this workspace.
2. If this workspace lives under WSL, run the bridge script instead of `uv` directly -- it handles mirroring to a native Windows path and syncing dependencies for you:
   ```bash
   ./outlookctl-bridge.sh doctor
   ```
   All four checks (`windows_os`, `pywin32`, `outlook_com`, `outlook_exe`) should show `"passed": true`. If `outlook_com` fails, start Classic Outlook first.
3. Confirm categories work end to end:
   ```bash
   ./outlookctl-bridge.sh category list
   ```
   This should return the categories already defined in your Outlook mailbox (Outlook ships several by default, e.g. "Red Category").
4. If this workspace does **not** live under WSL (already on a native Windows filesystem), the bridge script is unnecessary -- run `uv sync` and `uv run python -m outlookctl.cli doctor` directly from that folder in a native Windows terminal instead.

## How the Agent Runs Commands

Every command in this workspace's stages is run as:
```
./outlookctl-bridge.sh <command> [options]
```
(relative to `skills/outlook-automation/`, where the script lives). If the workspace is on a native Windows path instead of WSL, use `uv run --project "<path-to-outlookctl-src>" python -m outlookctl.cli <command> [options]` directly instead -- no bridging is needed in that case.

## Local Patch: Category Support

Upstream `outlookctl` (as of the version bundled here) has no command for Outlook Categories -- only folders (`move`) are supported natively. This workspace adds:

- `category list` -- enumerate the categories defined on your mailbox
- `category get --id <id> --store <store>` -- read the categories on one message
- `category set --id <id> --store <store> --categories "A,B" [--mode replace|add|remove]` -- assign categories
- `search --category <name>` -- filter search results by category (substring match)
- Every `list`/`search`/`get` result now includes a `categories` field automatically

This is implemented as three small, additive changes on top of the upstream `outlook_com.py`, `cli.py`, and `models.py`, following the exact patterns the tool already uses for `mark-read` (single-property mutation) and calendar event categories (which upstream already reads, just never exposed for mail or exposed as a filter). If you update to a newer upstream release, these three files will need the patch reapplied -- diff against the versions in this workspace's `skills/outlook-automation/outlookctl-src/` to see exactly what changed.

## Troubleshooting

See `../../skills/outlook-automation/reference/troubleshooting.md` for the full upstream guide (Outlook COM unavailable, pywin32 issues, security prompts, etc). It covers everything except the category commands, which are new in this bundle.
