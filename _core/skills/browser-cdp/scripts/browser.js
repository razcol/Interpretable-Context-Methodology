// Usage: node scripts/browser.js <start|stop|status> [--profile NAME] [--port N] [--headed]
import { parseArgs, run, startBrowser, stopBrowser, browserStatus, profileOf, CliError, EXIT, DEFAULT_PORT } from './lib.js';

run(async () => {
  const args = parseArgs(process.argv.slice(2), { strings: ['profile', 'port'], booleans: ['headed'] });
  const cmd = args._[0];
  const profile = profileOf(args);
  switch (cmd) {
    case 'start':
      return startBrowser({ profile, port: args.port ? Number(args.port) : DEFAULT_PORT, headed: Boolean(args.headed) });
    case 'stop':
      return stopBrowser(profile);
    case 'status':
      return browserStatus(profile);
    default:
      throw new CliError('USAGE', 'Usage: browser.js <start|stop|status> [--profile NAME] [--port N] [--headed]', EXIT.USAGE);
  }
});
