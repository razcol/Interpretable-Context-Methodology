// Usage: node scripts/navigate.js --url URL [--wait-for CSS] [--profile NAME] [--timeout MS]
// Opens the URL in a throwaway tab, waits until ready (load + network idle + fonts), reports status/title, closes the tab.
// Use it as a cheap "is this page reachable and ready" check before heavier commands.
import { parseArgs, run, withBrowser, freshPage, gotoStable, profileOf, timeoutOf } from './lib.js';

run(async () => {
  const args = parseArgs(process.argv.slice(2), { strings: ['url', 'wait-for', 'profile', 'timeout'], required: ['url'] });
  return withBrowser(profileOf(args), async (browser) => {
    const page = await freshPage(browser, { width: 1280, height: 800 });
    try {
      const t0 = Date.now();
      const nav = await gotoStable(page, args.url, { timeout: timeoutOf(args), waitFor: args.waitFor });
      return { url: args.url, ...nav, title: await page.title(), readyMs: Date.now() - t0 };
    } finally {
      await page.close();
    }
  });
});
