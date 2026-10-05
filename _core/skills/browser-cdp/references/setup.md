# Setup

What this is: a small Node project (puppeteer-core, pixelmatch, pngjs) that drives an installed Chrome over the DevTools Protocol.

## Requirements

- Node 20 or newer (`node -v`)
- npm
- Google Chrome or Chromium installed where the scripts run (WSL: `/usr/bin/google-chrome`)

## Install

```bash
cd <path-to>/browser-cdp
npm install
```

Dependencies are pinned to exact versions in `package.json`. `puppeteer-core` does not download a browser.
`puppeteer-core` is pinned to 24.43.1 because the 25.x line requires Node 22.12 or newer. Do not bump it without checking the Node version.

## Verify

```bash
node scripts/browser.js start
node scripts/navigate.js --url https://example.com/
node scripts/browser.js stop
```

Expect `"ok": true` and `"status": 200`.

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `BCDP_CHROME` | Path to the Chrome binary | auto-detected |
| `BCDP_HOME` | Where profiles and state files live | `~/.cache/browser-cdp` |
| `BCDP_NO_SANDBOX` | Set to `1` when running as root or in a container | unset |

## How this workspace uses it

Workspaces reference `SKILL.md` from their stage Inputs. They should check that Node and Chrome exist during their own `setup`.

## Not supported yet

- Windows Chrome attached from WSL. WSL2 NAT networking normally blocks `localhost` to Windows services. Mirrored networking would be needed.
- Attaching to a normal, logged-in Chrome profile. Chrome 136+ ignores debug ports on the default profile.
