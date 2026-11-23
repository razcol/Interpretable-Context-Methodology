// Non-destructive screenshot annotations for browser-cdp (module, not a CLI).
// Injects a temporary DOM/SVG overlay (#__bcdp-overlay) into the page, the caller captures, and the overlay is
// removed in a finally block right after the capture. No image library is involved.
// All text is written with textContent and all attributes with setAttribute (never innerHTML), and colors are
// validated against a strict pattern, so annotation input cannot inject markup or CSS into the page.
//
// Annotation schema (JSON array of objects, unknown keys and unknown types are USAGE errors):
//   {"type":"box",   "selector"?:css, "rect"?:{x,y,width,height}, "badge"?:number|string, "label"?:string, "color"?:string, "padding"?:number}
//   {"type":"arrow", "from"?:{x,y}|css, "to":{x,y}|css, "label"?:string, "color"?:string}
//   {"type":"badge", "selector"?:css, "x"?:number, "y"?:number, "text":string|number, "position"?:"top-left"|"top-right"|"bottom-left"|"bottom-right", "color"?:string}
// A box needs "selector" or "rect"; a badge needs "selector" or both "x" and "y". When both are given, the selector wins.
//
// Coordinates you pass (rect, points, x/y) are in the capture frame:
//   viewport capture   -> viewport pixels (overlay is position:fixed)
//   fullPage capture   -> document pixels (overlay is position:absolute, scroll offset added to selector rects)
//   element capture    -> pixels relative to the top-left of the captured element (overlay clipped to the element)
// Selectors are always resolved against the whole document, so inside an element capture they only draw where
// they intersect the captured element. Badges and labels sit on outer corners and are clamped inside the frame.
import fs from 'node:fs';
import { CliError, EXIT } from './lib.js';

export const OVERLAY_ID = '__bcdp-overlay';

const KEYS = {
  box: ['type', 'selector', 'rect', 'badge', 'label', 'color', 'padding'],
  arrow: ['type', 'from', 'to', 'label', 'color'],
  badge: ['type', 'selector', 'x', 'y', 'text', 'position', 'color'],
};
const POSITIONS = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];
const COLOR_RE = /^(#[0-9a-fA-F]{3,8}|[a-zA-Z]{3,20}|(rgb|hsl)a?\(\s*[\d.\s,%/-]+\))$/;
const MAX_TEXT = 120;

const usage = (msg, details) => new CliError('USAGE', msg, EXIT.USAGE, details);
const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

function checkString(a, where, key, { required = false } = {}) {
  const v = a[key];
  if (v === undefined) {
    if (required) throw usage(`${where}: "${key}" is required`);
    return;
  }
  if (typeof v !== 'string' || v.length === 0 || v.length > MAX_TEXT) throw usage(`${where}: "${key}" must be a non-empty string of at most ${MAX_TEXT} characters`);
}

function checkText(a, where, key, { required = false } = {}) {
  const v = a[key];
  if (v === undefined) {
    if (required) throw usage(`${where}: "${key}" is required`);
    return;
  }
  if (!(typeof v === 'string' && v.length > 0 && v.length <= MAX_TEXT) && !isNum(v)) throw usage(`${where}: "${key}" must be a number or a non-empty string of at most ${MAX_TEXT} characters`);
}

function checkPoint(v, where, key) {
  if (typeof v === 'string') {
    if (v.length === 0) throw usage(`${where}: "${key}" selector must not be empty`);
    return;
  }
  if (!isObj(v) || !isNum(v.x) || !isNum(v.y) || Object.keys(v).some((k) => k !== 'x' && k !== 'y')) {
    throw usage(`${where}: "${key}" must be {x, y} (numbers) or a CSS selector string`);
  }
}

/** Validate a parsed annotations array. Returns the array unchanged. Throws CliError USAGE (exit 1). */
export function validateAnnotations(list, from = 'annotations') {
  if (!Array.isArray(list)) throw usage(`${from} must be a JSON array`);
  list.forEach((a, i) => {
    const where = `${from}[${i}]`;
    if (!isObj(a)) throw usage(`${where} must be an object`);
    if (!Object.prototype.hasOwnProperty.call(KEYS, a.type)) throw usage(`${where}: unknown type "${a.type}". Allowed: ${Object.keys(KEYS).join(', ')}`);
    const unknown = Object.keys(a).filter((k) => !KEYS[a.type].includes(k));
    if (unknown.length) throw usage(`${where}: unknown key(s) ${unknown.map((k) => `"${k}"`).join(', ')} for type "${a.type}"`, { allowed: KEYS[a.type] });
    if (a.color !== undefined && (typeof a.color !== 'string' || !COLOR_RE.test(a.color))) throw usage(`${where}: "color" must be a hex, named, rgb() or hsl() color`);
    if (a.selector !== undefined) checkString(a, where, 'selector');
    if (a.type === 'box') {
      if (a.selector === undefined && a.rect === undefined) throw usage(`${where}: box needs "selector" or "rect"`);
      if (a.rect !== undefined) {
        const r = a.rect;
        if (!isObj(r) || !['x', 'y', 'width', 'height'].every((k) => isNum(r[k])) || Object.keys(r).some((k) => !['x', 'y', 'width', 'height'].includes(k)) || r.width <= 0 || r.height <= 0) {
          throw usage(`${where}: "rect" must be {x, y, width, height} with positive width and height`);
        }
      }
      checkText(a, where, 'badge');
      checkString(a, where, 'label');
      if (a.padding !== undefined && (!isNum(a.padding) || a.padding < 0 || a.padding > 200)) throw usage(`${where}: "padding" must be a number between 0 and 200`);
    } else if (a.type === 'arrow') {
      if (a.to === undefined) throw usage(`${where}: arrow needs "to"`);
      checkPoint(a.to, where, 'to');
      if (a.from !== undefined) checkPoint(a.from, where, 'from');
      checkString(a, where, 'label');
    } else {
      checkText(a, where, 'text', { required: true });
      if (a.selector === undefined && !(isNum(a.x) && isNum(a.y))) throw usage(`${where}: badge needs "selector" or both "x" and "y"`);
      if (a.x !== undefined && !isNum(a.x)) throw usage(`${where}: "x" must be a number`);
      if (a.y !== undefined && !isNum(a.y)) throw usage(`${where}: "y" must be a number`);
      if (a.position !== undefined && !POSITIONS.includes(a.position)) throw usage(`${where}: "position" must be one of ${POSITIONS.join(', ')}`);
    }
  });
  return list;
}

/** Parse annotation JSON text. Bad JSON, non-array, unknown type or bad field -> CliError USAGE (exit 1). */
export function parseAnnotations(raw, from = 'annotations') {
  let list;
  try {
    list = JSON.parse(raw);
  } catch (e) {
    throw usage(`${from} is not valid JSON: ${e.message}`);
  }
  return validateAnnotations(list, from);
}

/** From parsed CLI args (--annotations / --annotations-file). Returns [] when neither is given. */
export function loadAnnotations(args) {
  if (args.annotations !== undefined && args.annotationsFile !== undefined) {
    throw usage('Use either --annotations or --annotations-file, not both');
  }
  if (args.annotations !== undefined) return parseAnnotations(args.annotations, '--annotations');
  if (args.annotationsFile !== undefined) {
    let raw;
    try {
      raw = fs.readFileSync(args.annotationsFile, 'utf8');
    } catch {
      throw new CliError('FILE_NOT_FOUND', `Annotations file not readable: ${args.annotationsFile}`, EXIT.USAGE);
    }
    return parseAnnotations(raw, '--annotations-file');
  }
  return [];
}

/** Remove the overlay if present. Safe to call at any time. */
export async function removeOverlay(page) {
  await page.evaluate((id) => {
    document.querySelectorAll(`#${id}`).forEach((n) => n.remove());
  }, OVERLAY_ID);
}

/**
 * Draw the overlay. The frame is 'element' when `target` (an ElementHandle) is given, 'document' for fullPage,
 * otherwise 'viewport'. Returns the per-annotation results array.
 */
export async function applyAnnotations(page, annotations, { fullPage = false, target = null } = {}) {
  const frame = target ? 'element' : fullPage ? 'document' : 'viewport';
  return page.evaluate(drawOverlay, annotations, frame, OVERLAY_ID, target);
}

/**
 * Apply annotations, run capture(), and always remove the overlay right after capture.
 * Returns { value, annotations } where annotations is the results array, or undefined when none were requested
 * (the page is then not touched at all).
 */
export async function withAnnotations(page, annotations, { fullPage = false, target = null } = {}, capture) {
  if (!annotations || annotations.length === 0) return { value: await capture(), annotations: undefined };
  let results;
  try {
    results = await applyAnnotations(page, annotations, { fullPage, target });
    const value = await capture();
    return { value, annotations: results };
  } finally {
    await removeOverlay(page).catch(() => {});
  }
}

// Runs inside the page. Must be self-contained (no outer references).
function drawOverlay(annotations, frameKind, overlayId, target) {
  const NS = 'http://www.w3.org/2000/svg';
  const DEFAULT = '#ff2d55';
  const FONT = '600 12px/1 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
  const R = 11; // badge radius
  const MARGIN = 2;

  document.querySelectorAll(`#${overlayId}`).forEach((n) => n.remove());

  const sx = window.scrollX;
  const sy = window.scrollY;
  const de = document.documentElement;
  let origin = { x: 0, y: 0 };
  let W;
  let H;
  let toLocal;
  if (frameKind === 'viewport') {
    W = window.innerWidth;
    H = window.innerHeight;
    toLocal = (r) => ({ x: r.left, y: r.top, width: r.width, height: r.height });
  } else if (frameKind === 'document') {
    W = Math.max(de.scrollWidth, document.body ? document.body.scrollWidth : 0);
    H = Math.max(de.scrollHeight, document.body ? document.body.scrollHeight : 0);
    toLocal = (r) => ({ x: r.left + sx, y: r.top + sy, width: r.width, height: r.height });
  } else {
    const t = target.getBoundingClientRect();
    origin = { x: t.left + sx, y: t.top + sy };
    W = t.width;
    H = t.height;
    toLocal = (r) => ({ x: r.left + sx - origin.x, y: r.top + sy - origin.y, width: r.width, height: r.height });
  }

  const box = document.createElement('div');
  box.id = overlayId;
  box.setAttribute('aria-hidden', 'true');
  const fixed = frameKind === 'viewport';
  const css = {
    all: 'initial',
    position: fixed ? 'fixed' : 'absolute',
    left: `${fixed ? 0 : origin.x}px`,
    top: `${fixed ? 0 : origin.y}px`,
    width: `${W}px`,
    height: `${H}px`,
    margin: '0',
    padding: '0',
    border: '0',
    overflow: 'hidden',
    'pointer-events': 'none',
    'z-index': '2147483647',
    display: 'block',
    contain: 'strict',
  };
  for (const [k, v] of Object.entries(css)) box.style.setProperty(k, v, 'important');
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('width', String(W));
  svg.setAttribute('height', String(H));
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.style.cssText = 'display:block;position:absolute;left:0;top:0;pointer-events:none;overflow:hidden';
  box.appendChild(svg);
  de.appendChild(box);
  if (!fixed) {
    // Correct for positioned ancestors (html { position: relative } and similar).
    const b = box.getBoundingClientRect();
    const dx = origin.x - sx - b.left;
    const dy = origin.y - sy - b.top;
    if (Math.abs(dx) > 0.5) box.style.setProperty('left', `${origin.x + dx}px`, 'important');
    if (Math.abs(dy) > 0.5) box.style.setProperty('top', `${origin.y + dy}px`, 'important');
  }

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi < lo ? lo : hi, v));
  const round = (v) => Math.round(v * 10) / 10;
  const rr = (r) => ({ x: round(r.x), y: round(r.y), width: round(r.width), height: round(r.height) });

  const el = (name, attrs, parent = svg) => {
    const n = document.createElementNS(NS, name);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
    parent.appendChild(n);
    return n;
  };

  const measure = (text) => {
    const t = el('text', { x: 0, y: 0, style: `font:${FONT}`, visibility: 'hidden' });
    t.textContent = text;
    const w = t.getBBox().width;
    t.remove();
    return w;
  };

  // Pill (rounded rect + text) whose top-left is (x, y), clamped to the frame. Returns its rect.
  const pill = (text, x, y, color, minWidth = 0) => {
    const s = String(text);
    const w = Math.max(minWidth, Math.ceil(measure(s)) + 12);
    const h = 20;
    const px = clamp(x, MARGIN, W - w - MARGIN);
    const py = clamp(y, MARGIN, H - h - MARGIN);
    el('rect', { x: px, y: py, width: w, height: h, rx: h / 2, fill: color, stroke: '#ffffff', 'stroke-width': 1.5 });
    const t = el('text', { x: px + w / 2, y: py + h / 2, 'text-anchor': 'middle', 'dominant-baseline': 'central', fill: '#ffffff', style: `font:${FONT}` });
    t.textContent = s;
    return { x: px, y: py, width: w, height: h };
  };

  // Badge centered on (cx, cy), clamped so the whole badge stays inside the frame.
  const badge = (text, cx, cy, color) => {
    const s = String(text);
    const w = Math.max(2 * R, Math.ceil(measure(s)) + 12);
    return pill(s, cx - w / 2, cy - R, color, 2 * R);
  };

  const corner = (r, position) => {
    const left = position.endsWith('left');
    const top = position.startsWith('top');
    return { x: left ? r.x : r.x + r.width, y: top ? r.y : r.y + r.height };
  };

  const find = (selector) => {
    let node;
    try {
      node = document.querySelector(selector);
    } catch {
      return { error: `invalid selector: ${selector}` };
    }
    if (!node) return { error: `selector not found: ${selector}` };
    const r = toLocal(node.getBoundingClientRect());
    if (r.width <= 0 && r.height <= 0) return { error: `selector matches a zero-size element: ${selector}` };
    return { rect: r };
  };

  const intersects = (r) => r.x < W && r.y < H && r.x + r.width > 0 && r.y + r.height > 0;

  // Point on the boundary of rect r along the line from its center toward p.
  const edgePoint = (r, p) => {
    const cx = r.x + r.width / 2;
    const cy = r.y + r.height / 2;
    const dx = p.x - cx;
    const dy = p.y - cy;
    if (dx === 0 && dy === 0) return { x: cx, y: cy };
    const k = Math.min(dx !== 0 ? r.width / 2 / Math.abs(dx) : Infinity, dy !== 0 ? r.height / 2 / Math.abs(dy) : Infinity);
    return { x: cx + dx * k, y: cy + dy * k };
  };
  const center = (r) => ({ x: r.x + r.width / 2, y: r.y + r.height / 2 });

  const results = [];
  annotations.forEach((a, index) => {
    const res = { index, type: a.type };
    results.push(res);
    const color = a.color || DEFAULT;
    try {
      if (a.type === 'box') {
        let rect;
        if (a.selector !== undefined) {
          res.selector = a.selector;
          const f = find(a.selector);
          if (f.error) return Object.assign(res, { applied: false, reason: f.error });
          rect = f.rect;
        } else {
          rect = { x: a.rect.x, y: a.rect.y, width: a.rect.width, height: a.rect.height };
        }
        if (!intersects(rect)) return Object.assign(res, { applied: false, rect: rr(rect), reason: 'outside the capture area' });
        const pad = a.padding === undefined ? 4 : a.padding;
        const r = { x: rect.x - pad, y: rect.y - pad, width: rect.width + 2 * pad, height: rect.height + 2 * pad };
        el('rect', { x: r.x, y: r.y, width: r.width, height: r.height, fill: 'none', stroke: color, 'stroke-width': 3, rx: 2 });
        let labelX = r.x;
        if (a.badge !== undefined) {
          const c = corner(r, 'top-left');
          const b = badge(a.badge, c.x, c.y, color);
          labelX = b.x + b.width + 4;
        }
        if (a.label !== undefined) {
          const w = Math.ceil(measure(String(a.label))) + 12;
          const above = r.y - 20 - 4;
          const y = above >= MARGIN ? above : r.y + r.height + 4; // no room above: below the bottom edge
          pill(a.label, clamp(labelX, MARGIN, W - w - MARGIN), y, color);
        }
        res.applied = true;
        res.rect = rr(rect);
      } else if (a.type === 'badge') {
        let anchor;
        if (a.selector !== undefined) {
          res.selector = a.selector;
          const f = find(a.selector);
          if (f.error) return Object.assign(res, { applied: false, reason: f.error });
          if (!intersects(f.rect)) return Object.assign(res, { applied: false, rect: rr(f.rect), reason: 'outside the capture area' });
          anchor = corner(f.rect, a.position || 'top-left');
        } else {
          anchor = { x: a.x, y: a.y };
          if (anchor.x < 0 || anchor.y < 0 || anchor.x > W || anchor.y > H) return Object.assign(res, { applied: false, reason: 'outside the capture area' });
        }
        const b = badge(a.text, anchor.x, anchor.y, color);
        res.applied = true;
        res.rect = rr(b);
      } else {
        // arrow
        const resolve = (v) => {
          if (typeof v === 'string') {
            const f = find(v);
            return f.error ? { error: f.error } : { rect: f.rect };
          }
          return { point: { x: v.x, y: v.y } };
        };
        const to = resolve(a.to);
        const from = a.from === undefined ? { auto: true } : resolve(a.from);
        const selector = typeof a.to === 'string' ? a.to : typeof a.from === 'string' ? a.from : undefined;
        if (selector !== undefined) res.selector = selector;
        const err = to.error || from.error;
        if (err) return Object.assign(res, { applied: false, reason: err });
        const toC = to.rect ? center(to.rect) : to.point;
        let fromC;
        if (from.auto) {
          // Default tail: 90px away diagonally, on whichever side has room.
          fromC = { x: toC.x - 90 >= 40 ? toC.x - 90 : toC.x + 90, y: toC.y - 90 >= 40 ? toC.y - 90 : toC.y + 90 };
          fromC = { x: clamp(fromC.x, 0, W), y: clamp(fromC.y, 0, H) };
        } else {
          fromC = from.rect ? center(from.rect) : from.point;
        }
        const end = to.rect ? edgePoint(to.rect, fromC) : toC;
        const start = from.rect ? edgePoint(from.rect, toC) : fromC;
        const len = Math.hypot(end.x - start.x, end.y - start.y);
        if (len < 1) return Object.assign(res, { applied: false, reason: 'arrow start and end coincide' });
        const ux = (end.x - start.x) / len;
        const uy = (end.y - start.y) / len;
        const head = Math.min(14, len * 0.6);
        const bx = end.x - ux * head;
        const by = end.y - uy * head;
        el('line', { x1: start.x, y1: start.y, x2: bx, y2: by, stroke: color, 'stroke-width': 3, 'stroke-linecap': 'round' });
        el('polygon', { points: `${end.x},${end.y} ${bx - uy * head * 0.5},${by + ux * head * 0.5} ${bx + uy * head * 0.5},${by - ux * head * 0.5}`, fill: color });
        if (a.label !== undefined) {
          const w = Math.ceil(measure(String(a.label))) + 12;
          const h = 20;
          // Center the pill just behind the tail so it does not sit on the shaft or the target.
          const off = (w / 2) * Math.abs(ux) + (h / 2) * Math.abs(uy) + 4;
          pill(a.label, start.x - ux * off - w / 2, start.y - uy * off - h / 2, color);
        }
        res.applied = true;
        const minX = Math.min(start.x, end.x);
        const minY = Math.min(start.y, end.y);
        res.rect = rr({ x: minX, y: minY, width: Math.max(start.x, end.x) - minX, height: Math.max(start.y, end.y) - minY });
      }
    } catch (e) {
      res.applied = false;
      res.reason = `annotation failed: ${e && e.message ? e.message : String(e)}`;
    }
  });
  return results;
}
