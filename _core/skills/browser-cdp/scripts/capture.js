// Usage: node scripts/capture.js --url URL [--viewport 1280x800] [--settle-ms 0] [--wait-for CSS]
//        [--include-requests] [--out FILE.json] [--profile NAME] [--timeout MS]
// Records console messages, uncaught page errors, failed requests and HTTP >= 400 responses during one navigation.
// favicon.ico failures are ignored (Chrome requests it automatically and it is noise).
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs, run, withBrowser, freshPage, gotoStable, parseViewport, ensureDir, profileOf, timeoutOf } from './lib.js';

const CAP = 50;
const isFavicon = (u) => /\/favicon\.ico(\?|$)/.test(u || '');

run(async () => {
  const args = parseArgs(process.argv.slice(2), {
    strings: ['url', 'viewport', 'settle-ms', 'wait-for', 'out', 'profile', 'timeout'],
    booleans: ['include-requests'],
    required: ['url'],
  });
  const vp = parseViewport(args.viewport || '1280x800');
  const timeout = timeoutOf(args);

  return withBrowser(profileOf(args), async (browser) => {
    const page = await freshPage(browser, vp);
    const consoleMessages = [];
    const pageErrors = [];
    const failedRequests = [];
    const httpErrors = [];
    const requests = [];
    const byType = {};
    let total = 0;

    page.on('console', (m) => {
      const loc = m.location();
      if (isFavicon(loc && loc.url)) return;
      consoleMessages.push({ type: m.type(), text: m.text(), source: loc && loc.url ? `${loc.url}:${loc.lineNumber ?? 0}` : undefined });
    });
    page.on('pageerror', (e) => pageErrors.push({ message: e.message }));
    page.on('request', (r) => {
      total++;
      byType[r.resourceType()] = (byType[r.resourceType()] || 0) + 1;
      if (args.includeRequests) requests.push({ method: r.method(), url: r.url(), resourceType: r.resourceType() });
    });
    page.on('requestfailed', (r) => {
      if (!isFavicon(r.url())) failedRequests.push({ url: r.url(), resourceType: r.resourceType(), reason: r.failure() && r.failure().errorText });
    });
    page.on('response', (r) => {
      if (r.status() >= 400 && !isFavicon(r.url())) httpErrors.push({ url: r.url(), status: r.status(), resourceType: r.request().resourceType() });
    });

    let nav;
    try {
      nav = await gotoStable(page, args.url, { timeout, waitFor: args.waitFor });
      if (args.settleMs) await new Promise((r) => setTimeout(r, Number(args.settleMs)));
    } finally {
      await page.close();
    }

    const errorsOnly = consoleMessages.filter((m) => m.type === 'error');
    const warnings = consoleMessages.filter((m) => m.type === 'warn' || m.type === 'warning');
    const full = { consoleMessages, pageErrors, failedRequests, httpErrors, ...(args.includeRequests ? { requests } : {}) };
    const cap = (arr) => arr.slice(0, CAP);
    const result = {
      url: args.url,
      finalUrl: nav.finalUrl,
      status: nav.status,
      networkSettled: nav.networkSettled,
      summary: {
        consoleErrors: errorsOnly.length,
        consoleWarnings: warnings.length,
        pageErrors: pageErrors.length,
        failedRequests: failedRequests.length,
        httpErrors: httpErrors.length,
        totalRequests: total,
        requestsByType: byType,
      },
      consoleErrors: cap(errorsOnly),
      pageErrors: cap(pageErrors),
      failedRequests: cap(failedRequests),
      httpErrors: cap(httpErrors),
      truncated: [errorsOnly, pageErrors, failedRequests, httpErrors].some((a) => a.length > CAP),
    };
    if (args.out) {
      ensureDir(path.dirname(path.resolve(args.out)));
      fs.writeFileSync(args.out, JSON.stringify({ ...result, ...full }, null, 2));
      result.detailsFile = path.resolve(args.out);
    }
    return result;
  });
});
