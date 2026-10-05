// Usage: node scripts/interact.js (--steps '<json array>' | --steps-file FILE) [--url URL] [--new-tab]
//        [--viewport 1280x800] [--out-dir DIR] [--profile NAME] [--timeout MS]
// Runs steps in order on the current tab (the tab is kept open between calls so later calls continue the flow).
// Stops at the first failing step. Actions:
//   {"action":"goto","url":"https://..."}
//   {"action":"click","selector":"css"}
//   {"action":"type","selector":"css","text":"...","clear":true}   (clear defaults to true)
//   {"action":"press","key":"Enter"}
//   {"action":"select","selector":"css","value":"..."}
//   {"action":"wait_for","selector":"css","state":"visible|hidden"}  or  {"action":"wait_for","text":"..."}
//   {"action":"get_text","selector":"css"}
//   {"action":"assert_text","contains":"...","selector":"css(optional, default body)"}
//   {"action":"assert_url","contains":"..."}
//   {"action":"screenshot","name":"file-base"}
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs, run, withBrowser, freshPage, gotoStable, freezeAnimations, parseViewport, ensureDir, fileInfo, profileOf, timeoutOf, waitForSelector, CliError, EXIT, DEFAULT_OUT } from './lib.js';

const ACTIONS = ['goto', 'click', 'type', 'press', 'select', 'wait_for', 'get_text', 'assert_text', 'assert_url', 'screenshot'];

async function settle(page) {
  try {
    await page.waitForNetworkIdle({ idleTime: 300, timeout: 5000 });
  } catch {
    /* best effort */
  }
}

function loadSteps(args) {
  let raw = args.steps;
  if (!raw && args.stepsFile) raw = fs.readFileSync(args.stepsFile, 'utf8');
  if (!raw) throw new CliError('USAGE', 'Provide --steps JSON or --steps-file FILE', EXIT.USAGE);
  let steps;
  try {
    steps = JSON.parse(raw);
  } catch (e) {
    throw new CliError('USAGE', `Steps are not valid JSON: ${e.message}`, EXIT.USAGE);
  }
  if (!Array.isArray(steps) || steps.length === 0) throw new CliError('USAGE', 'Steps must be a non-empty JSON array', EXIT.USAGE);
  steps.forEach((s, i) => {
    if (!s || !ACTIONS.includes(s.action)) throw new CliError('USAGE', `Step ${i}: unknown action "${s && s.action}". Allowed: ${ACTIONS.join(', ')}`, EXIT.USAGE);
  });
  return steps;
}

const need = (s, i, key) => {
  if (s[key] === undefined) throw new CliError('USAGE', `Step ${i} (${s.action}) needs "${key}"`, EXIT.USAGE);
  return s[key];
};

run(async () => {
  const args = parseArgs(process.argv.slice(2), {
    strings: ['steps', 'steps-file', 'url', 'viewport', 'out-dir', 'profile', 'timeout'],
    booleans: ['new-tab'],
  });
  const steps = loadSteps(args);
  const timeout = timeoutOf(args);
  const outDir = ensureDir(args.outDir || DEFAULT_OUT);
  const vp = parseViewport(args.viewport || '1280x800');

  return withBrowser(profileOf(args), async (browser) => {
    let page;
    if (!args.newTab) {
      // Only real content tabs count. Chrome also exposes internal pages (chrome://omnibox-popup..., devtools) as "pages".
      const pages = (await browser.pages()).filter((p) => !p.isClosed() && /^(https?:|file:|about:blank$)/.test(p.url()));
      page = [...pages].reverse().find((p) => p.url() !== 'about:blank') || pages[pages.length - 1];
    }
    if (!page) page = await freshPage(browser, vp);
    else await page.setViewport({ ...vp, deviceScaleFactor: 1 });

    const consoleErrors = [];
    page.on('console', (m) => m.type() === 'error' && consoleErrors.push(m.text()));
    page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${e.message}`));

    const results = [];
    if (args.url) {
      const nav = await gotoStable(page, args.url, { timeout });
      results.push({ step: -1, action: 'goto(--url)', status: nav.status, url: nav.finalUrl });
    }

    for (let i = 0; i < steps.length; i++) {
      const s = steps[i];
      try {
        const r = { step: i, action: s.action };
        switch (s.action) {
          case 'goto': {
            const nav = await gotoStable(page, need(s, i, 'url'), { timeout });
            Object.assign(r, { status: nav.status, url: nav.finalUrl });
            break;
          }
          case 'click': {
            const el = await waitForSelector(page, need(s, i, 'selector'), timeout, { visible: true });
            await el.click();
            await settle(page);
            break;
          }
          case 'type': {
            const el = await waitForSelector(page, need(s, i, 'selector'), timeout, { visible: true });
            if (s.clear !== false) await el.evaluate((e) => { e.focus(); if ('value' in e) e.value = ''; });
            await el.type(String(need(s, i, 'text')));
            break;
          }
          case 'press':
            await page.keyboard.press(need(s, i, 'key'));
            await settle(page);
            break;
          case 'select': {
            await waitForSelector(page, need(s, i, 'selector'), timeout);
            const chosen = await page.select(s.selector, String(need(s, i, 'value')));
            if (chosen.length === 0) throw new CliError('ELEMENT_NOT_FOUND', `Option "${s.value}" not found in ${s.selector}`, EXIT.ELEMENT);
            await settle(page);
            break;
          }
          case 'wait_for':
            if (s.text !== undefined) {
              await page.waitForFunction((t) => document.body && document.body.innerText.includes(t), { timeout }, String(s.text));
            } else {
              await waitForSelector(page, need(s, i, 'selector'), timeout, s.state === 'hidden' ? { hidden: true } : { visible: true });
            }
            break;
          case 'get_text': {
            const el = await waitForSelector(page, need(s, i, 'selector'), timeout);
            r.text = (await el.evaluate((e) => e.innerText)).slice(0, 2000);
            break;
          }
          case 'assert_text': {
            const text = await page.evaluate((sel) => (sel ? document.querySelector(sel) : document.body)?.innerText ?? null, s.selector || null);
            if (text === null) throw new CliError('ELEMENT_NOT_FOUND', `Selector "${s.selector}" not found`, EXIT.ELEMENT);
            if (!text.includes(String(need(s, i, 'contains')))) throw new CliError('ASSERTION_FAILED', `Text does not contain "${s.contains}"`, EXIT.ASSERT);
            break;
          }
          case 'assert_url':
            if (!page.url().includes(String(need(s, i, 'contains')))) throw new CliError('ASSERTION_FAILED', `URL "${page.url()}" does not contain "${s.contains}"`, EXIT.ASSERT);
            break;
          case 'screenshot': {
            await freezeAnimations(page);
            const file = path.join(outDir, `${String(need(s, i, 'name')).replace(/[^a-zA-Z0-9._-]/g, '-')}.png`);
            await page.screenshot({ path: file });
            r.file = fileInfo(file);
            break;
          }
          default:
            break;
        }
        results.push(r);
      } catch (e) {
        const base = e instanceof CliError ? e : new CliError(e && e.name === 'TimeoutError' ? 'TIMEOUT' : 'STEP_FAILED', e.message, e && e.name === 'TimeoutError' ? EXIT.TIMEOUT : EXIT.INTERNAL);
        throw new CliError(base.code, `Step ${i} (${s.action}) failed: ${base.message}`, base.exit, { failedStep: i, completed: results, currentUrl: page.url() });
      }
    }
    return { currentUrl: page.url(), stepsRun: steps.length, results, consoleErrors: consoleErrors.slice(0, 20) };
  });
});
