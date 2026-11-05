# figma-cli setup

The exporter is the single executable `tools/figma-cli`, built from `~/cli/figma-cli` with `npm run ship:workspace`. Do not run npm in this workspace and do not read the binary as source. A figma-cli change ends with a commit in `~/cli/figma-cli`, `npm run ship:workspace`, and a commit of the binary here.

Shipped build: figma-cli `8896b3f` (2026-11-05). `--version` prints the commit the binary was built from; a `-dirty` mark means uncommitted source.

## Runtime and token

Needs Node 20.6 or later (for `--env-file`). The token is `FIGMA_ACCESS_TOKEN` in `/home/dev/cli/figma-cli/.env`. Load it with Node, never by hand:

```bash
FIGMA="node --env-file=/home/dev/cli/figma-cli/.env /home/dev/ai-system/workspaces/figma-section-fields/tools/figma-cli"
$FIGMA --version
```

Never `cat`, `echo` or `source` that file in a command, never paste the token into a command line, and never write it into a record. If the user pastes a token into chat, tell them to rotate it.

## Calling it

Always the absolute path above. Always put the Figma URL in single quotes, because it contains `&`:

```bash
$FIGMA inspect 'https://www.figma.com/design/<key>/<name>?node-id=1404-7715&m=dev'
```

Commands, flags, files and exit codes are in `shared/export-contract.md`.
