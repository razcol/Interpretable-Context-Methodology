# figma-cli setup

The exporter is the single executable `tools/figma-cli`, built from `~/cli/figma-cli` with `npm run ship:workspace`. Do not run npm in this workspace and do not read the binary as source. A figma-cli change ends with a commit in `~/cli/figma-cli`, `npm run ship:workspace`, and a commit of the binary here.

Shipped build: figma-cli `9da06e8` (2026-11-08). `--version` prints the commit the binary was built from; a `-dirty` mark means uncommitted source.

## Runtime and token

Needs Node 20.6 or later (for `--env-file`). The token is `FIGMA_ACCESS_TOKEN` in the env file that the "Figma token file" line of `<data-root>/workspaces/figma-section-fields/repos.md` names (`<figma env>` below; `setup` Q3 sets it). Load it with Node, never by hand:

```bash
FIGMA="node --env-file=<figma env> <workspace>/tools/figma-cli"
$FIGMA --version
```

Both are real absolute paths: `<figma env>` with `~` expanded (the shell does not expand `~` after `--env-file=`), and `<workspace>` this workspace in the ai-system checkout the run is in (`CLAUDE.md`), so a run calls its own checkout's binary.

Never `cat`, `echo` or `source` that file in a command, never paste the token into a command line, and never write it into a record. If the user pastes a token into chat, tell them to rotate it.

## Calling it

Always the absolute paths above. Always put the Figma URL in single quotes, because it contains `&`:

```bash
$FIGMA inspect 'https://www.figma.com/design/<key>/<name>?node-id=1404-7715&m=dev'
```

Commands, flags, files and exit codes are in `shared/export-contract.md`.
