# Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `BROWSER_NOT_RUNNING` (exit 2) | No Chrome for that profile | `node scripts/browser.js start [--profile X]` |
| `BROWSER_UNREACHABLE` (exit 2) | State file exists but Chrome died | `browser.js stop`, then `start` |
| `PORT_IN_USE` on start | Another process answers CDP on that port | Use `--port` with a free port |
| `CHROME_NOT_FOUND` | No Chrome at known paths | Set `BCDP_CHROME` |
| `BROWSER_MODE_MISMATCH` | Profile running headless, asked headed (or reverse) | `stop`, then `start` with the right flag |
| Chrome fails to start as root/container | Sandbox | `BCDP_NO_SANDBOX=1` |
| `NAVIGATION_FAILED` with `ERR_UNSAFE_PORT` | Chrome blocks some ports (for example 1, 22, 6000) | Use a normal port |
| `NAVIGATION_FAILED` with `ERR_CONNECTION_REFUSED` | Nothing listens on that URL | Start the app first |
| `ELEMENT_NOT_FOUND` | Selector wrong or element appears late | Run `snapshot.js --mode dom`, fix the selector, or raise `--timeout` |
| Screenshot differs between runs | Live content, random data, lazy images | Use `--selector`, `--wait-for`, or a tolerance via `diff.js --max-diff-ratio` |
| `networkSettled: false` | Page keeps polling | Normal for chatty pages. Add `--wait-for` on a stable element |
| Cookies gone after restart | Session cookies, or an unclean shutdown | Use `browser.js stop` (graceful), not kill. Persistent cookies survive |
| Headed window does not appear | WSLg not available | Check `echo $DISPLAY`. Use headless |
