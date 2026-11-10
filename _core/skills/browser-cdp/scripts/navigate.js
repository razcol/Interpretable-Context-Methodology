// Usage: node scripts/navigate.js --url URL [--wait-for CSS] [--fresh-context] [--profile NAME] [--timeout MS]
// Opens the URL in a throwaway tab, waits until ready (load + network idle + fonts), reports status/title, closes the tab.
// Use it as a cheap "is this page reachable and ready" check before heavier commands.
// --fresh-context opens the tab in a new browser context: no cookies, storage or cache from the profile.
import { parseArgs, run, withBrowser, freshPage, gotoStable, profileOf, timeoutOf } from './lib.js';

run(async () => {
  const args = parseArgs(process.argv.slice(2), { strings: ['url', 'wait-for', 'profile', 'timeout'], booleans: ['fresh-context'], required: ['url'] });
  return withBrowser(profileOf(args), async (browser) => {
    const context = args.freshContext ? await browser.createBrowserContext() : null;
    const page = await freshPage(context || browser, { width: 1280, height: 800 });
    try {
      const t0 = Date.now();
      const nav = await gotoStable(page, args.url, { timeout: timeoutOf(args), waitFor: args.waitFor });
      return { url: args.url, ...nav, title: await page.title(), readyMs: Date.now() - t0, ...(context ? { freshContext: true } : {}) };
    } finally {
      await page.close();
      if (context) await context.close().catch(() => {});
    }
  });
});
