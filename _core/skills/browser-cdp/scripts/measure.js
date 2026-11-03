// Usage: node scripts/measure.js --url URL [--viewports 1920x1080,1440x900,1100x800] [--selector CSS]
//        [--out-dir DIR] [--name BASE] [--wait-for CSS] [--profile NAME] [--timeout MS]
// Local pages only: http://localhost, http://127.0.0.1 or file://.
// For each viewport: horizontal overflow of the page, the box of --selector, and a screenshot of it
// (or of the viewport without --selector). Exit 11 when any viewport overflows.
import path from 'node:path';
import { parseArgs, run, withBrowser, freshPage, gotoStable, freezeAnimations, parseViewport, slugFromUrl, ensureDir, fileInfo, profileOf, timeoutOf, waitForSelector, CliError, EXIT, DEFAULT_OUT } from './lib.js';

const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1']);

/** The verify step measures your own dev server or a local file, nothing else. */
export function checkLocalUrl(raw) {
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new CliError('USAGE', `Not a URL: "${raw}"`, EXIT.USAGE);
  }
  const local = url.protocol === 'file:' || (url.protocol === 'http:' && LOCAL_HOSTS.has(url.hostname));
  if (!local) throw new CliError('USAGE', `measure.js only opens http://localhost, http://127.0.0.1 or file:// pages (got ${url.protocol}//${url.hostname})`, EXIT.USAGE);
  return url.href;
}

/** Runs in the page. Takes the selector as data; no string is evaluated. */
function measurePage(selector) {
  const scroller = document.scrollingElement || document.documentElement;
  const out = { scrollWidth: scroller.scrollWidth, innerWidth: window.innerWidth, sectionBox: null };
  if (selector) {
    const el = document.querySelector(selector);
    if (el) {
      const r = el.getBoundingClientRect();
      out.sectionBox = { x: Math.round(r.x), y: Math.round(r.y + window.scrollY), width: Math.round(r.width), height: Math.round(r.height) };
    }
  }
  return out;
}

run(async () => {
  const args = parseArgs(process.argv.slice(2), {
    strings: ['url', 'out-dir', 'viewports', 'name', 'selector', 'wait-for', 'profile', 'timeout'],
    required: ['url'],
  });
  const url = checkLocalUrl(args.url);
  const viewports = (args.viewports || '1920x1080,1440x900,1100x800').split(',').map((s) => parseViewport(s.trim()));
  const outDir = ensureDir(args.outDir || DEFAULT_OUT);
  const base = args.name || slugFromUrl(url);
  const timeout = timeoutOf(args);

  const result = await withBrowser(profileOf(args), async (browser) => {
    const results = [];
    for (const vp of viewports) {
      const page = await freshPage(browser, vp);
      try {
        await gotoStable(page, url, { timeout, waitFor: args.waitFor });
        await freezeAnimations(page);
        const measured = await page.evaluate(measurePage, args.selector || null);
        const file = path.join(outDir, `${base}__${vp.width}x${vp.height}__measure.png`);
        if (args.selector) {
          const el = await waitForSelector(page, args.selector, timeout);
          await el.screenshot({ path: file });
        } else {
          await page.screenshot({ path: file });
        }
        const overflowPx = Math.max(0, measured.scrollWidth - measured.innerWidth);
        results.push({ viewport: `${vp.width}x${vp.height}`, ...measured, overflow: overflowPx > 0, overflowPx, screenshot: fileInfo(file) });
      } finally {
        await page.close();
      }
    }
    return { url, selector: args.selector || null, results, pass: results.every((entry) => !entry.overflow) };
  });
  if (!result.pass) {
    const widths = result.results.filter((entry) => entry.overflow).map((entry) => `${entry.viewport} (+${entry.overflowPx}px)`);
    throw new CliError('OVERFLOW_DETECTED', `The page scrolls sideways at ${widths.join(', ')}`, EXIT.OVERFLOW, result);
  }
  return result;
});
