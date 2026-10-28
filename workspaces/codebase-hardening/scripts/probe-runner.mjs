#!/usr/bin/env node
// Bookkeeping and deterministic validation for probe reports, convention candidates, and rule blocks.
// It never reads the target repo except to compare the HEAD sha. No dependencies.
//
// Usage:
//   node probe-runner.mjs list --probes <dir> [--probes <dir>...] --out <dir>
//   node probe-runner.mjs validate --out <dir> [--repo <dir>]
//   node probe-runner.mjs validate-candidates <file> [--final]
//   node probe-runner.mjs validate-rules <file>

import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { join, basename } from 'node:path';
import { execFileSync } from 'node:child_process';

const [cmd, ...rest] = process.argv.slice(2);
const values = (name) => rest.flatMap((a, i) => (a === `--${name}` ? [rest[i + 1]] : []));
const one = (name) => values(name)[0];
const has = (name) => rest.includes(`--${name}`);

const SECTIONS = ['Method', 'Population', 'Distribution', 'Trend', 'Exemplars', 'Outliers', 'Interpretation', 'Unknowns'];
const MAX_CHARS = 6000;
const MAX_INTERPRETATION = 1200;

function frontMatter(text) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n/);
  if (!m) return null;
  const fm = {};
  for (const line of m[1].split('\n')) {
    const i = line.indexOf(':');
    if (i > 0) fm[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return fm;
}

function sectionBody(text, name) {
  const m = text.match(new RegExp(`^## ${name}\\n([\\s\\S]*?)(?=^## |(?![\\s\\S]))`, 'm'));
  return m ? m[1].trim() : null;
}

function validateReport(file, outDir, headSha) {
  const errors = [];
  const text = readFileSync(file, 'utf8');
  const fm = frontMatter(text);
  if (!fm) return ['missing front matter'];
  for (const k of ['probe', 'question', 'status', 'confidence', 'repo_sha', 'generated']) if (!fm[k]) errors.push(`front matter missing "${k}"`);
  if (fm.probe && fm.probe !== basename(file, '.md')) errors.push(`probe "${fm.probe}" does not match file name`);
  if (fm.status !== 'complete') errors.push(`status is "${fm.status}", expected "complete"`);
  if (!['high', 'medium', 'low'].includes(fm.confidence)) errors.push(`confidence is "${fm.confidence}", expected high, medium, or low`);
  if (text.length > MAX_CHARS) errors.push(`report is ${text.length} characters, cap is ${MAX_CHARS}`);
  let last = -1;
  for (const s of SECTIONS) {
    const idx = text.search(new RegExp(`^## ${s}$`, 'm'));
    if (idx < 0) errors.push(`missing section "${s}"`);
    else if (idx < last) errors.push(`section "${s}" is out of order`);
    else last = idx;
  }
  const method = sectionBody(text, 'Method');
  if (method !== null && !/`[^`]+`/.test(method)) errors.push('Method has no command in backticks');
  const dist = sectionBody(text, 'Distribution');
  if (dist !== null && !/^\|.+\|$/m.test(dist)) errors.push('Distribution has no table');
  const ex = sectionBody(text, 'Exemplars');
  if (ex !== null) {
    for (const line of ex.split('\n').filter((l) => l.startsWith('-'))) {
      const refs = line.match(/[^\s`,]+:\d+/g) || [];
      if (refs.length > 3) errors.push(`exemplar line has ${refs.length} pointers, max 3: ${line.slice(0, 60)}`);
    }
  }
  const interp = sectionBody(text, 'Interpretation');
  if (interp !== null) {
    if (!interp || /TODO/.test(interp)) errors.push('Interpretation is empty or still TODO');
    if (interp.length > MAX_INTERPRETATION) errors.push(`Interpretation is ${interp.length} characters, cap is ${MAX_INTERPRETATION}`);
  }
  const unk = sectionBody(text, 'Unknowns');
  if (unk !== null && (!unk || /TODO/.test(unk))) errors.push('Unknowns is empty or still TODO');
  for (const ref of new Set(text.match(/evidence\/[\w.\-]+/g) || [])) {
    if (!existsSync(join(outDir, ref))) errors.push(`referenced evidence file is missing: ${ref}`);
  }
  if (headSha && fm.repo_sha && fm.repo_sha !== headSha) errors.push(`stale: report sha ${fm.repo_sha.slice(0, 8)} differs from HEAD ${headSha.slice(0, 8)}`);
  return errors;
}

// --- block validation (candidates "C-001" and rules "R-001") ------------------------------
function parseBlocks(text, prefix) {
  const blocks = [];
  const re = new RegExp(`^### (${prefix}-\\d{3}): (.+)$`, 'gm');
  const heads = [...text.matchAll(re)];
  heads.forEach((h, i) => {
    const body = text.slice(h.index + h[0].length, i + 1 < heads.length ? heads[i + 1].index : undefined);
    const fields = {};
    for (const line of body.split('\n')) {
      const m = line.match(/^- ([a-z_]+):\s*(.*)$/);
      if (m) fields[m[1]] = m[2].trim();
    }
    blocks.push({ id: h[1], title: h[2], fields });
  });
  return blocks;
}

function validateCandidates(file, final) {
  const errors = [];
  const blocks = parseBlocks(readFileSync(file, 'utf8'), 'C');
  if (!blocks.length) errors.push('no candidate blocks found (### C-001: title)');
  const seen = new Set();
  for (const b of blocks) {
    if (seen.has(b.id)) errors.push(`${b.id}: duplicate id`);
    seen.add(b.id);
    for (const k of ['rule', 'dominant', 'evidence', 'trend', 'risk_if_wrong', 'corroboration', 'decision']) if (!b.fields[k]) errors.push(`${b.id}: missing "${k}"`);
    const d = b.fields.decision;
    if (d && !['pending', 'ratified', 'rejected', 'changed'].includes(d)) errors.push(`${b.id}: decision "${d}" is not allowed`);
    if (final && d === 'pending') errors.push(`${b.id}: decision is still pending`);
    if (final && (d === 'ratified' || d === 'changed') && /^none/i.test(b.fields.corroboration || '') && !b.fields.ratifier_note) {
      errors.push(`${b.id}: no corroboration and no ratifier_note accepting a single probe`);
    }
  }
  return errors;
}

function validateRules(file) {
  const errors = [];
  const blocks = parseBlocks(readFileSync(file, 'utf8'), 'R');
  if (!blocks.length) errors.push('no rule blocks found (### R-001: title)');
  const seen = new Set();
  for (const b of blocks) {
    const f = b.fields;
    if (seen.has(b.id)) errors.push(`${b.id}: duplicate id`);
    seen.add(b.id);
    for (const k of ['status', 'source', 'rationale', 'evidence', 'mechanism', 'ladder', 'violations', 'confidence']) if (!f[k]) errors.push(`${b.id}: missing "${k}"`);
    if (!['READY', 'DEFERRED', 'DOCS-ONLY', 'DROPPED'].includes(f.status)) errors.push(`${b.id}: status "${f.status}" is not allowed`);
    if (!['1', '2', '3', '4', '5'].includes(f.ladder)) errors.push(`${b.id}: ladder "${f.ladder}" must be 1 to 5`);
    if (f.status !== 'DOCS-ONLY' && f.status !== 'DROPPED' && !f.dry_run_cmd) errors.push(`${b.id}: missing "dry_run_cmd"`);
    const n = Number(f.violations);
    if (f.status === 'READY' && !(f.violations === '0')) errors.push(`${b.id}: READY requires violations 0, found "${f.violations}"`);
    if (f.status === 'DEFERRED') {
      if (!Number.isInteger(n) || n < 1) errors.push(`${b.id}: DEFERRED requires violations of 1 or more, found "${f.violations}"`);
      if (!['skip', 'cleanup-first'].includes(f.decision)) errors.push(`${b.id}: DEFERRED requires decision skip or cleanup-first`);
    }
    if (f.status === 'DOCS-ONLY' && f.ladder !== '5') errors.push(`${b.id}: DOCS-ONLY requires ladder 5`);
    if (f.status === 'DROPPED' && f.decision !== 'drop') errors.push(`${b.id}: DROPPED requires decision drop`);
    if (f.status === 'READY' && f.ladder === '5') errors.push(`${b.id}: ladder 5 cannot be READY`);
  }
  return errors;
}

function report(title, errors) {
  if (errors.length) { console.log(`FAIL ${title}`); errors.forEach((e) => console.log(`  - ${e}`)); } else console.log(`PASS ${title}`);
  return errors.length;
}

if (cmd === 'list') {
  const out = one('out');
  if (!out || !values('probes').length) { console.error('usage: list --probes <dir>... --out <dir>'); process.exit(2); }
  for (const dir of values('probes')) {
    for (const f of readdirSync(dir).filter((n) => n.endsWith('.md') && n !== 'CONTEXT.md').sort()) {
      const id = basename(f, '.md');
      const rp = join(out, 'reports', `${id}.md`);
      let state = 'pending';
      if (existsSync(rp)) {
        const fm = frontMatter(readFileSync(rp, 'utf8'));
        state = !fm ? 'invalid' : fm.status === 'complete' ? 'done' : fm.status === 'needs-interpretation' ? 'needs-interpretation' : 'invalid';
      }
      console.log(`${state.padEnd(22)}${id.padEnd(28)}${join(dir, f)}`);
    }
  }
} else if (cmd === 'validate') {
  const out = one('out');
  if (!out) { console.error('usage: validate --out <dir> [--repo <dir>]'); process.exit(2); }
  const dir = join(out, 'reports');
  const headSha = one('repo') ? execFileSync('git', ['-C', one('repo'), 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim() : null;
  const files = existsSync(dir) ? readdirSync(dir).filter((n) => n.endsWith('.md')).sort() : [];
  let bad = files.length ? 0 : report('reports', ['no reports found']);
  for (const f of files) bad += report(f, validateReport(join(dir, f), out, headSha)) ? 1 : 0;
  console.log(`${files.length - bad} of ${files.length} reports valid`);
  process.exit(bad ? 1 : 0);
} else if (cmd === 'validate-candidates' && rest[0]) {
  process.exit(report(rest[0], validateCandidates(rest[0], has('final'))) ? 1 : 0);
} else if (cmd === 'validate-rules' && rest[0]) {
  process.exit(report(rest[0], validateRules(rest[0])) ? 1 : 0);
} else {
  console.error('commands: list | validate | validate-candidates | validate-rules');
  process.exit(2);
}
