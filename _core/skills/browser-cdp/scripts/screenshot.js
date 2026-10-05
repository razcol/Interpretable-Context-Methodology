// Usage: node scripts/screenshot.js --url URL [--viewports 1280x800,375x812] [--full-page | --selector CSS]
//        [--out-dir DIR (default: ~/.cache/browser-cdp/out or $BCDP_OUT)] [--name BASE] [--wait-for CSS] [--profile NAME] [--timeout MS]
// Output files: <out-dir>/<name>__<W>x<H>[__full|__sel-<slug>].png  (name defaults to a slug of the URL)
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs, run, withBrowser, freshPage, gotoStable, freezeAnimations, parseViewport, slugFromUrl, ensureDir, fileInfo, profileOf, timeoutOf, waitForSelector, CliError, EXIT, DEFAULT_OUT } from './lib.js';

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) };
}

run(async () => {
  const args = parseArgs(process.argv.slice(2), {
    strings: ['url', 'out-dir', 'viewports', 'name', 'selector', 'wait-for', 'profile', 'timeout'],
    booleans: ['full-page'],
    required: ['url'],
  });
  if (args.selector && args.fullPage) throw new CliError('USAGE', 'Use either --selector or --full-page, not both', EXIT.USAGE);
  const viewports = (args.viewports || '1280x800').split(',').map((s) => parseViewport(s.trim()));
  const outDir = ensureDir(args.outDir || DEFAULT_OUT);
  const base = args.name || slugFromUrl(args.url);
  const timeout = timeoutOf(args);
  const selSlug = args.selector ? args.selector.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 30) : '';
  const suffix = args.selector ? `__sel-${selSlug}` : args.fullPage ? '__full' : '';

  return withBrowser(profileOf(args), async (browser) => {
    const screenshots = [];
    let nav;
    for (const vp of viewports) {
      const page = await freshPage(browser, vp);
      try {
        nav = await gotoStable(page, args.url, { timeout, waitFor: args.waitFor });
        await freezeAnimations(page);
        const file = path.join(outDir, `${base}__${vp.width}x${vp.height}${suffix}.png`);
        if (args.selector) {
          const el = await waitForSelector(page, args.selector, timeout);
          await el.screenshot({ path: file });
        } else {
          await page.screenshot({ path: file, fullPage: Boolean(args.fullPage) });
        }
        screenshots.push({ viewport: `${vp.width}x${vp.height}`, ...fileInfo(file), image: pngSize(file), networkSettled: nav.networkSettled });
      } finally {
        await page.close();
      }
    }
    return { url: args.url, finalUrl: nav.finalUrl, status: nav.status, screenshots };
  });
});
