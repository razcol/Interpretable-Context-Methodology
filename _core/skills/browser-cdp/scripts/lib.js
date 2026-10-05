// Shared helpers for browser-cdp scripts.
// Contract: every script prints exactly one JSON object to stdout.
//   success: { "ok": true, ... }            exit 0
//   failure: { "ok": false, "error": {...} } non-zero exit (see EXIT)
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';
import puppeteer from 'puppeteer-core';

export const EXIT = { USAGE: 1, BROWSER: 2, NAVIGATION: 3, ELEMENT: 4, TIMEOUT: 5, ASSERT: 6, DIFF: 10, INTERNAL: 99 };

export class CliError extends Error {
  constructor(code, message, exit = EXIT.INTERNAL, details) {
    super(message);
    this.code = code;
    this.exit = exit;
    this.details = details;
  }
}

const camel = (s) => s.replace(/-([a-z])/g, (_, c) => c.toUpperCase());

/** Minimal strict arg parser. Unknown options are errors so agents cannot typo silently. */
export function parseArgs(argv, { strings = [], booleans = [], required = [] } = {}) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) {
      out._.push(a);
      continue;
    }
    const key = a.slice(2);
    if (booleans.includes(key)) {
      out[camel(key)] = true;
      continue;
    }
    if (!strings.includes(key)) {
      throw new CliError('USAGE', `Unknown option --${key}`, EXIT.USAGE, { allowed: [...strings, ...booleans].map((k) => `--${k}`) });
    }
    const v = argv[++i];
    if (v === undefined) throw new CliError('USAGE', `Option --${key} needs a value`, EXIT.USAGE);
    out[camel(key)] = v;
  }
  for (const r of required) {
    if (out[camel(r)] === undefined) throw new CliError('USAGE', `Missing required option --${r}`, EXIT.USAGE);
  }
  return out;
}

export async function run(main) {
  let result;
  let code = 0;
  try {
    result = { ok: true, ...(await main()) };
  } catch (e) {
    const err = mapError(e);
    code = err.exit;
    result = { ok: false, error: { code: err.code, message: err.message, ...(err.details ? { details: err.details } : {}) } };
  }
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  process.exit(code);
}

function mapError(e) {
  if (e instanceof CliError) return e;
  if (e && e.name === 'TimeoutError') return new CliError('TIMEOUT', e.message, EXIT.TIMEOUT);
  return new CliError('INTERNAL', e && e.message ? e.message : String(e), EXIT.INTERNAL);
}

// ---------------------------------------------------------------- paths

export const HOME = process.env.BCDP_HOME || path.join(os.homedir(), '.cache', 'browser-cdp');
export const DEFAULT_PORT = 9333;
// Where screenshots/snapshots go when --out-dir is not given. Outside the skill folder on purpose.
export const DEFAULT_OUT = process.env.BCDP_OUT || path.join(HOME, 'out');

const stateFile = (profile) => path.join(HOME, `${profile}.json`);
const profileDir = (profile) => path.join(HOME, 'profiles', profile);

function validProfile(profile) {
  if (!/^[a-z0-9][a-z0-9-]{0,40}$/.test(profile)) {
    throw new CliError('USAGE', `Invalid profile name "${profile}" (use lowercase letters, digits, hyphens)`, EXIT.USAGE);
  }
  return profile;
}

// ---------------------------------------------------------------- browser lifecycle

function findChrome() {
  const candidates = [process.env.BCDP_CHROME, '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/snap/bin/chromium'].filter(Boolean);
  const found = candidates.find((p) => fs.existsSync(p));
  if (!found) {
    throw new CliError('CHROME_NOT_FOUND', 'No Chrome/Chromium binary found. Set BCDP_CHROME to its path.', EXIT.BROWSER, { tried: candidates });
  }
  return found;
}

async function versionInfo(port, timeoutMs = 1500) {
  try {
    const r = await fetch(`http://127.0.0.1:${port}/json/version`, { signal: AbortSignal.timeout(timeoutMs) });
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  }
}

function readState(profile) {
  try {
    return JSON.parse(fs.readFileSync(stateFile(profile), 'utf8'));
  } catch {
    return null;
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function browserStatus(profile) {
  validProfile(profile);
  const st = readState(profile);
  if (!st) return { running: false, profile };
  const info = await versionInfo(st.port);
  if (!info) return { running: false, profile, stale: true };
  return { running: true, profile, port: st.port, pid: st.pid, headed: st.headed, browser: info.Browser, userDataDir: st.userDataDir };
}

export async function startBrowser({ profile, port = DEFAULT_PORT, headed = false }) {
  validProfile(profile);
  const existing = await browserStatus(profile);
  if (existing.running) {
    if (existing.headed !== headed) {
      throw new CliError('BROWSER_MODE_MISMATCH', `Profile "${profile}" is already running ${existing.headed ? 'headed' : 'headless'}. Run stop first.`, EXIT.BROWSER);
    }
    return { ...existing, alreadyRunning: true };
  }
  if (await versionInfo(port)) {
    throw new CliError('PORT_IN_USE', `Something already answers CDP on port ${port}. Pick another with --port.`, EXIT.BROWSER);
  }
  const chrome = findChrome();
  const userDataDir = profileDir(profile);
  fs.mkdirSync(userDataDir, { recursive: true });
  const args = [
    `--remote-debugging-port=${port}`,
    '--remote-debugging-address=127.0.0.1',
    `--user-data-dir=${userDataDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--hide-scrollbars',
    '--mute-audio',
    '--force-color-profile=srgb',
    '--font-render-hinting=none',
    '--disable-lcd-text',
  ];
  if (!headed) args.push('--headless=new');
  if (process.env.BCDP_NO_SANDBOX === '1') args.push('--no-sandbox');
  args.push('about:blank');
  const child = spawn(chrome, args, { detached: true, stdio: 'ignore' });
  child.unref();
  for (let i = 0; i < 50; i++) {
    const info = await versionInfo(port);
    if (info) {
      fs.mkdirSync(HOME, { recursive: true });
      const st = { pid: child.pid, port, profile, headed, userDataDir, chrome, startedAt: new Date().toISOString() };
      fs.writeFileSync(stateFile(profile), JSON.stringify(st, null, 2));
      return { running: true, profile, port, pid: child.pid, headed, browser: info.Browser, userDataDir };
    }
    await sleep(200);
  }
  throw new CliError('BROWSER_START_TIMEOUT', `Chrome did not open CDP on port ${port} within 10s`, EXIT.BROWSER, { chrome });
}

export async function stopBrowser(profile) {
  validProfile(profile);
  const st = readState(profile);
  if (!st) return { stopped: false, reason: 'not running', profile };
  // Ask Chrome to close itself over CDP: a graceful shutdown flushes cookies/storage to the profile.
  // A bare SIGTERM can lose recent cookies. Signals are only the fallback.
  let method = 'cdp';
  try {
    const b = await puppeteer.connect({ browserURL: `http://127.0.0.1:${st.port}`, defaultViewport: null });
    await b.close();
  } catch {
    method = 'sigterm';
    try {
      process.kill(st.pid, 'SIGTERM');
    } catch {
      /* already gone */
    }
  }
  const alive = () => {
    try {
      process.kill(st.pid, 0);
      return true;
    } catch {
      return false;
    }
  };
  for (let i = 0; i < 50 && alive(); i++) await sleep(200);
  if (alive()) {
    method = 'sigkill';
    try {
      process.kill(st.pid, 'SIGKILL');
    } catch {
      /* gone */
    }
  }
  fs.rmSync(stateFile(profile), { force: true });
  return { stopped: true, profile, method };
}

/** Connect to the running browser for a profile, run fn, always disconnect. */
export async function withBrowser(profile, fn) {
  const status = await browserStatus(profile);
  if (!status.running) {
    throw new CliError('BROWSER_NOT_RUNNING', `No browser running for profile "${profile}". Start one: node scripts/browser.js start`, EXIT.BROWSER);
  }
  let browser;
  try {
    browser = await puppeteer.connect({ browserURL: `http://127.0.0.1:${status.port}`, defaultViewport: null });
  } catch (e) {
    throw new CliError('BROWSER_UNREACHABLE', `Could not connect to Chrome on port ${status.port}: ${e.message}`, EXIT.BROWSER);
  }
  try {
    return await fn(browser);
  } finally {
    await browser.disconnect();
  }
}

// ---------------------------------------------------------------- page helpers

export function parseViewport(s) {
  const m = /^(\d{2,5})x(\d{2,5})$/.exec(s || '');
  if (!m) throw new CliError('USAGE', `Bad viewport "${s}". Use WIDTHxHEIGHT, e.g. 1280x800`, EXIT.USAGE);
  return { width: Number(m[1]), height: Number(m[2]) };
}

export async function freshPage(browser, viewport) {
  const page = await browser.newPage();
  await page.setViewport({ ...viewport, deviceScaleFactor: 1 });
  // The profile persists on disk, so without this a repeat visit can come back as 304 and depend on cache state.
  await page.setCacheEnabled(false);
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  return page;
}

export async function gotoStable(page, url, { timeout = 30000, waitFor } = {}) {
  if (!/^(https?|file):\/\//.test(url) && url !== 'about:blank') {
    throw new CliError('USAGE', `URL must start with http://, https:// or file:// (got "${url}")`, EXIT.USAGE);
  }
  let res;
  try {
    res = await page.goto(url, { waitUntil: 'load', timeout });
  } catch (e) {
    if (e && e.name === 'TimeoutError') throw new CliError('TIMEOUT', `Navigation to ${url} exceeded ${timeout}ms`, EXIT.TIMEOUT);
    throw new CliError('NAVIGATION_FAILED', `Navigation to ${url} failed: ${e.message}`, EXIT.NAVIGATION);
  }
  let settled = true;
  try {
    await page.waitForNetworkIdle({ idleTime: 500, timeout: Math.min(timeout, 10000) });
  } catch {
    settled = false;
  }
  if (waitFor) await waitForSelector(page, waitFor, timeout);
  await page.evaluate(() => (document.fonts ? document.fonts.ready.then(() => true) : true));
  return { status: res ? res.status() : null, finalUrl: page.url(), networkSettled: settled };
}

export async function waitForSelector(page, selector, timeout = 30000, opts = {}) {
  try {
    return await page.waitForSelector(selector, { timeout, ...opts });
  } catch (e) {
    if (e && e.name === 'TimeoutError') throw new CliError('ELEMENT_NOT_FOUND', `Selector "${selector}" not found within ${timeout}ms`, EXIT.ELEMENT, { selector });
    throw e;
  }
}

export async function freezeAnimations(page) {
  await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important;scroll-behavior:auto!important}' });
}

// ---------------------------------------------------------------- files

export function slugFromUrl(url) {
  const u = new URL(url);
  const raw = `${u.hostname}${u.pathname}${u.search}`.toLowerCase();
  return raw.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80) || 'page';
}

export function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
  return path.resolve(dir);
}

export function sha256File(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

export function fileInfo(file) {
  const abs = path.resolve(file);
  return { path: abs, bytes: fs.statSync(abs).size, sha256: sha256File(abs) };
}

export const COMMON_STRINGS = ['profile', 'timeout'];
export const profileOf = (args) => args.profile || 'default';
export const timeoutOf = (args) => (args.timeout ? Number(args.timeout) : 30000);
