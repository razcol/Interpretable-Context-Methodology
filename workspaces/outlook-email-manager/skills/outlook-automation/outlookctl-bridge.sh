#!/usr/bin/env bash
# outlookctl-bridge.sh
#
# Runs outlookctl from this WSL-hosted workspace against the real Outlook
# COM session on the Windows host.
#
# WHY THIS EXISTS
# `outlookctl` depends on pywin32, which only works from a Windows-native
# Python process with a genuine interactive Windows logon session. Two
# approaches that look plausible do NOT work reliably, and must not be used:
#
#   1. Running `uv`/python directly from a WSL/Linux shell.
#      pywin32 has no Linux wheel -- `uv sync` fails outright (confirmed:
#      "pywin32 (v312) only has wheels for win32/win_amd64/win_arm64").
#
#   2. Invoking `powershell.exe`/`uv` from WSL but pointing --project at a
#      \\wsl$\... or \\wsl.localhost\... UNC path.
#      This intermittently fails ("Project directory does not exist",
#      "network name is no longer available", etc.) because a powershell.exe
#      process spawned via WSL interop runs in its own logon session, and
#      mapped/UNC access to the WSL 9P share is scoped to the interactive
#      desktop session, not that spawned session. It may appear to work once
#      and then fail the next time -- do not trust a single successful run.
#
# THE RELIABLE PATTERN (what this script does)
#   1. Mirror outlookctl-src (source + pyproject/uv.lock, NOT .venv) to a
#      native Windows path: %LOCALAPPDATA%\outlookctl-bridge
#   2. Run `uv` from that native path via powershell.exe. uv.exe is invoked
#      by its full path since the installer does not always put it on PATH.
#   3. Capture PowerShell's redirected output (UTF-16LE with BOM by default)
#      and re-decode it to UTF-8 so JSON output is readable.
#
# USAGE
#   ./outlookctl-bridge.sh <outlookctl-cli args...>
#   e.g. ./outlookctl-bridge.sh doctor
#        ./outlookctl-bridge.sh category list
#        ./outlookctl-bridge.sh list --folder inbox --unread-only --count 20
#
# Exit code is outlookctl's own exit code (propagated from PowerShell).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/outlookctl-src"

if [[ ! -f "${SRC_DIR}/pyproject.toml" ]]; then
  echo "error: ${SRC_DIR}/pyproject.toml not found -- is outlookctl-src in place?" >&2
  exit 1
fi

# Resolve the Windows-native mirror directory. %LOCALAPPDATA% on the Windows
# side, translated to its /mnt/c/... equivalent for the rsync below.
WIN_LOCALAPPDATA="$(powershell.exe -NoProfile -Command '$env:LOCALAPPDATA' | tr -d '\r\n')"
if [[ -z "${WIN_LOCALAPPDATA}" ]]; then
  echo "error: could not resolve %LOCALAPPDATA% via powershell.exe" >&2
  exit 1
fi

# Convert e.g. C:\Users\me\AppData\Local -> /mnt/c/Users/me/AppData/Local
WSL_LOCALAPPDATA="/mnt/$(echo "${WIN_LOCALAPPDATA:0:1}" | tr '[:upper:]' '[:lower:]')${WIN_LOCALAPPDATA:2}"
WSL_LOCALAPPDATA="${WSL_LOCALAPPDATA//\\//}"
MIRROR_DIR_WSL="${WSL_LOCALAPPDATA}/outlookctl-bridge"
MIRROR_DIR_WIN="${WIN_LOCALAPPDATA}\\outlookctl-bridge"

mkdir -p "${MIRROR_DIR_WSL}"

# Mirror source, pyproject, lockfile -- never the WSL-side .venv (it's Linux
# ELF binaries and would be useless/harmful on Windows).
rsync -a --delete \
  --exclude='.venv' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  "${SRC_DIR}/" "${MIRROR_DIR_WSL}/"

# Locate uv.exe on the Windows side (installer commonly puts it in
# %USERPROFILE%\.local\bin, which is not always on PATH).
UV_EXE='$env:USERPROFILE\.local\bin\uv.exe'

OUT_FILE_WIN="${MIRROR_DIR_WIN}\\_bridge_out.tmp"
OUT_FILE_WSL="${MIRROR_DIR_WSL}/_bridge_out.tmp"

# Build the outlookctl args as a single PowerShell-safe argument list.
ARGS=("$@")
PS_ARGS=""
for a in "${ARGS[@]}"; do
  esc="${a//\"/\`\"}"
  PS_ARGS+=" \"${esc}\""
done

PS_COMMAND="[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; \$env:PYTHONIOENCODING = 'utf-8'; & ${UV_EXE} run --project '${MIRROR_DIR_WIN}' python -m outlookctl.cli${PS_ARGS} *> '${OUT_FILE_WIN}'; exit \$LASTEXITCODE"

powershell.exe -NoProfile -Command "${PS_COMMAND}"
PS_EXIT=$?

if [[ -f "${OUT_FILE_WSL}" ]]; then
  iconv -f UTF-16LE -t UTF-8 "${OUT_FILE_WSL}" 2>/dev/null | sed '1s/^\xEF\xBB\xBF//' || cat "${OUT_FILE_WSL}"
  rm -f "${OUT_FILE_WSL}"
else
  echo "error: no output captured from outlookctl (powershell exit ${PS_EXIT})" >&2
fi

exit "${PS_EXIT}"
