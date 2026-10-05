// Usage: node scripts/state.js <command> [options]
//   cookies-get   [--domain D | --url U] [--out FILE] [--show-values]
//   cookies-set   --file FILE                       (JSON array as written by cookies-get --out)
//   cookies-clear (--domain D | --all)
//   storage-get   --url U [--area local|session] [--out FILE] [--show-values]
//   storage-set   --url U --key K --value V [--area local|session]
//   storage-clear --url U [--area local|session]
// Secrets: values are redacted on stdout unless --show-values. --out files hold full values (mode 0600):
// keep them out of git. Cookies also persist automatically in the browser profile (see browser.js --profile).
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs, run, withBrowser, freshPage, gotoStable, ensureDir, profileOf, timeoutOf, CliError, EXIT } from './lib.js';

const SET_FIELDS = ['name', 'value', 'url', 'domain', 'path', 'secure', 'httpOnly', 'sameSite', 'expires', 'priority', 'sameParty', 'sourceScheme', 'sourcePort', 'partitionKey'];
const redact = (v) => `<redacted len=${String(v).length}>`;

const domainMatches = (cookieDomain, wanted) => {
  const c = cookieDomain.replace(/^\./, '').toLowerCase();
  const w = wanted.replace(/^\./, '').toLowerCase();
  return c === w || c.endsWith(`.${w}`) || w.endsWith(`.${c}`);
};

function writeSecret(file, data) {
  const abs = path.resolve(file);
  ensureDir(path.dirname(abs));
  fs.writeFileSync(abs, JSON.stringify(data, null, 2), { mode: 0o600 });
  fs.chmodSync(abs, 0o600);
  return abs;
}

function domainFilter(args) {
  if (args.domain) return args.domain;
  if (args.url) return new URL(args.url).hostname;
  return null;
}

run(async () => {
  const args = parseArgs(process.argv.slice(2), {
    strings: ['domain', 'url', 'file', 'out', 'key', 'value', 'area', 'profile', 'timeout'],
    booleans: ['show-values', 'all'],
  });
  const cmd = args._[0];
  const area = args.area || 'local';
  if (!['local', 'session'].includes(area)) throw new CliError('USAGE', '--area must be local or session', EXIT.USAGE);
  const storageName = area === 'local' ? 'localStorage' : 'sessionStorage';
  const timeout = timeoutOf(args);

  return withBrowser(profileOf(args), async (browser) => {
    const cdp = await browser.target().createCDPSession();
    try {
      switch (cmd) {
        case 'cookies-get': {
          const { cookies } = await cdp.send('Storage.getCookies');
          const dom = domainFilter(args);
          const list = dom ? cookies.filter((c) => domainMatches(c.domain, dom)) : cookies;
          const shown = list.map((c) => ({ name: c.name, domain: c.domain, path: c.path, secure: c.secure, httpOnly: c.httpOnly, sameSite: c.sameSite, expires: c.expires, value: args.showValues ? c.value : redact(c.value) }));
          const result = { count: list.length, cookies: shown };
          if (args.out) result.file = writeSecret(args.out, list);
          return result;
        }
        case 'cookies-set': {
          if (!args.file) throw new CliError('USAGE', 'cookies-set needs --file', EXIT.USAGE);
          let raw;
          try {
            raw = JSON.parse(fs.readFileSync(args.file, 'utf8'));
          } catch (e) {
            throw new CliError('USAGE', `Cannot read cookie file: ${e.message}`, EXIT.USAGE);
          }
          if (!Array.isArray(raw)) throw new CliError('USAGE', 'Cookie file must be a JSON array', EXIT.USAGE);
          const cookies = raw.map((c) => {
            const o = Object.fromEntries(Object.entries(c).filter(([k]) => SET_FIELDS.includes(k)));
            if (o.expires === -1 || o.expires === 0) delete o.expires;
            return o;
          });
          await cdp.send('Storage.setCookies', { cookies });
          return { set: cookies.length };
        }
        case 'cookies-clear': {
          if (!args.all && !args.domain) throw new CliError('USAGE', 'cookies-clear needs --domain D or --all', EXIT.USAGE);
          if (args.all) {
            await cdp.send('Storage.clearCookies');
            return { cleared: 'all' };
          }
          const { cookies } = await cdp.send('Storage.getCookies');
          const targets = cookies.filter((c) => domainMatches(c.domain, args.domain));
          const page = await freshPage(browser, { width: 800, height: 600 });
          try {
            const session = await page.createCDPSession();
            for (const c of targets) await session.send('Network.deleteCookies', { name: c.name, domain: c.domain, path: c.path });
          } finally {
            await page.close();
          }
          return { cleared: targets.length, domain: args.domain };
        }
        case 'storage-get':
        case 'storage-set':
        case 'storage-clear': {
          if (!args.url) throw new CliError('USAGE', `${cmd} needs --url (storage is per origin)`, EXIT.USAGE);
          const page = await freshPage(browser, { width: 800, height: 600 });
          try {
            await gotoStable(page, args.url, { timeout });
            if (cmd === 'storage-get') {
              const data = await page.evaluate((n) => Object.fromEntries(Object.entries(window[n])), storageName);
              const keys = Object.keys(data);
              const shown = Object.fromEntries(keys.map((k) => [k, args.showValues ? data[k] : redact(data[k])]));
              const result = { origin: new URL(page.url()).origin, area, count: keys.length, items: shown };
              if (args.out) result.file = writeSecret(args.out, data);
              return result;
            }
            if (cmd === 'storage-set') {
              if (args.key === undefined || args.value === undefined) throw new CliError('USAGE', 'storage-set needs --key and --value', EXIT.USAGE);
              await page.evaluate((n, k, v) => window[n].setItem(k, v), storageName, args.key, args.value);
              return { origin: new URL(page.url()).origin, area, set: args.key };
            }
            await page.evaluate((n) => window[n].clear(), storageName);
            return { origin: new URL(page.url()).origin, area, cleared: true };
          } finally {
            await page.close();
          }
        }
        default:
          throw new CliError('USAGE', 'Usage: state.js <cookies-get|cookies-set|cookies-clear|storage-get|storage-set|storage-clear> [options]', EXIT.USAGE);
      }
    } finally {
      await cdp.detach().catch(() => {});
    }
  });
});
