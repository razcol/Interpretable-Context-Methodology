// Usage: node scripts/snapshot.js --url URL --mode a11y|dom|html|text [--selector CSS] [--max-depth 8]
//        [--out FILE] [--out-dir DIR] [--viewport 1280x800] [--wait-for CSS] [--profile NAME] [--timeout MS]
// The snapshot is written to a file (path returned); stdout only carries stats so large pages do not flood the agent.
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs, run, withBrowser, freshPage, gotoStable, parseViewport, slugFromUrl, ensureDir, fileInfo, profileOf, timeoutOf, waitForSelector, CliError, EXIT, DEFAULT_OUT } from './lib.js';

const MODES = ['a11y', 'dom', 'html', 'text'];
const EXT = { a11y: 'json', dom: 'json', html: 'html', text: 'txt' };

async function a11y(page) {
  const client = await page.createCDPSession();
  await client.send('Accessibility.enable');
  const { nodes } = await client.send('Accessibility.getFullAXTree');
  const byId = new Map(nodes.map((n) => [n.nodeId, n]));
  const out = [];
  const NOISE_ROLES = new Set(['none', 'generic', 'InlineTextBox', 'LabelText', 'MenuListPopup']);
  const KEEP_FALSE = new Set(['expanded', 'selected', 'checked']); // false is meaningful for these
  const walk = (id, depth, parentName) => {
    const n = byId.get(id);
    if (!n) return;
    const role = n.role && n.role.value;
    const name = n.name && n.name.value ? n.name.value : '';
    // StaticText that only repeats its parent's name adds nothing for an agent.
    const duplicate = role === 'StaticText' && name === parentName;
    const keep = !n.ignored && role && !NOISE_ROLES.has(role) && !duplicate;
    if (keep) {
      const item = { depth, role, name };
      if (n.value && n.value.value !== undefined && n.value.value !== '') item.value = n.value.value;
      const props = {};
      for (const p of n.properties || []) {
        if (!['focusable', 'disabled', 'checked', 'expanded', 'selected', 'required', 'level', 'invalid'].includes(p.name)) continue;
        const v = p.value.value;
        if ((v === false || v === 'false') && !KEEP_FALSE.has(p.name)) continue;
        props[p.name] = v;
      }
      if (Object.keys(props).length) item.props = props;
      out.push(item);
    }
    for (const c of n.childIds || []) walk(c, keep ? depth + 1 : depth, keep ? name : parentName);
  };
  if (nodes.length) walk(nodes[0].nodeId, 0, '');
  return out;
}

// Runs inside the page (serialized by puppeteer), so it must stay self-contained.
function domTree(selector, maxDepth) {
  const root = selector ? document.querySelector(selector) : document.documentElement;
  const KEEP = ['href', 'src', 'type', 'name', 'role', 'aria-label', 'placeholder', 'value', 'alt', 'title', 'data-testid', 'for', 'action', 'method'];
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE']);
  let count = 0;
  const visit = (el, depth) => {
    count++;
    const node = { tag: el.tagName.toLowerCase() };
    if (el.id) node.id = el.id;
    if (el.classList.length) node.class = Array.from(el.classList).join(' ');
    const attrs = {};
    for (const a of KEEP) if (el.hasAttribute(a)) attrs[a] = el.getAttribute(a);
    if (Object.keys(attrs).length) node.attrs = attrs;
    const own = Array.from(el.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).filter(Boolean).join(' ');
    if (own) node.text = own.slice(0, 120);
    const kids = Array.from(el.children).filter((c) => !SKIP.has(c.tagName));
    if (kids.length) {
      if (depth >= maxDepth) node.childrenOmitted = kids.length;
      else node.children = kids.map((c) => visit(c, depth + 1));
    }
    return node;
  };
  return { tree: visit(root, 0), count };
}

run(async () => {
  const args = parseArgs(process.argv.slice(2), {
    strings: ['url', 'mode', 'selector', 'max-depth', 'out', 'out-dir', 'viewport', 'wait-for', 'profile', 'timeout'],
    required: ['url', 'mode'],
  });
  if (!MODES.includes(args.mode)) throw new CliError('USAGE', `--mode must be one of ${MODES.join(', ')}`, EXIT.USAGE);
  const timeout = timeoutOf(args);
  const maxDepth = args.maxDepth ? Number(args.maxDepth) : 8;
  const file = args.out ? path.resolve(args.out) : path.join(ensureDir(args.outDir || DEFAULT_OUT), `${slugFromUrl(args.url)}__${args.mode}.${EXT[args.mode]}`);
  ensureDir(path.dirname(file));

  return withBrowser(profileOf(args), async (browser) => {
    const page = await freshPage(browser, parseViewport(args.viewport || '1280x800'));
    try {
      const nav = await gotoStable(page, args.url, { timeout, waitFor: args.waitFor });
      if (args.selector) await waitForSelector(page, args.selector, timeout);
      let stats;
      if (args.mode === 'a11y') {
        const items = await a11y(page);
        fs.writeFileSync(file, JSON.stringify(items, null, 2));
        stats = { nodes: items.length };
      } else if (args.mode === 'dom') {
        const res = await page.evaluate(domTree, args.selector || null, maxDepth);
        fs.writeFileSync(file, JSON.stringify(res.tree, null, 2));
        stats = { elements: res.count, maxDepth };
      } else if (args.mode === 'html') {
        const html = await page.evaluate((sel) => (sel ? document.querySelector(sel) : document.documentElement).outerHTML, args.selector || null);
        fs.writeFileSync(file, html);
        stats = { chars: html.length };
      } else {
        const text = await page.evaluate((sel) => (sel ? document.querySelector(sel) : document.body).innerText, args.selector || null);
        fs.writeFileSync(file, text);
        stats = { chars: text.length };
      }
      return { url: args.url, finalUrl: nav.finalUrl, status: nav.status, mode: args.mode, ...(args.selector ? { selector: args.selector } : {}), ...stats, file: fileInfo(file) };
    } finally {
      await page.close();
    }
  });
});
