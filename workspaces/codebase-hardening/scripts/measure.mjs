#!/usr/bin/env node
// Runs one probe's measure block against a git repo and writes a report skeleton.
// The script fills every factual section. An agent fills Interpretation and Unknowns.
// Read-only on the target repo. Needs Node 18+ and git. No dependencies.
//
// Usage:
//   node measure.mjs --probe <probe.md> --repo <dir> --out <dir> [--days 90]

import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync, statSync } from 'node:fs';
import { basename, join, relative } from 'node:path';

const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : def;
};
const probePath = opt('probe');
const repo = opt('repo');
const out = opt('out');
if (!probePath || !repo || !out) {
  console.error('usage: node measure.mjs --probe <probe.md> --repo <dir> --out <dir> [--days 90]');
  process.exit(2);
}

const git = (...a) =>
  execFileSync('git', ['-C', repo, ...a], { encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });

function globToRegex(glob) {
  let re = '';
  let depth = 0;
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*') {
      if (glob[i + 1] === '*') {
        if (glob[i + 2] === '/') { re += '(?:.*/)?'; i += 2; } else { re += '.*'; i += 1; }
      } else re += '[^/]*';
    } else if (c === '?') re += '[^/]';
    else if (c === '{') { re += '(?:'; depth++; }
    else if (c === '}' && depth > 0) { re += ')'; depth--; }
    else if (c === ',' && depth > 0) re += '|';
    else if ('.+^$()|[]\\'.includes(c)) re += '\\' + c;
    else re += c;
  }
  return new RegExp(`^${re}$`);
}

// --- read the probe contract -------------------------------------------------
const md = readFileSync(probePath, 'utf8');
const id = basename(probePath, '.md');
const question = (md.match(/^Question:\s*(.+)$/m) || [])[1] || id;
const block = md.match(/```json measure\s*\n([\s\S]*?)```/);
if (!block) { console.error(`no "json measure" block in ${probePath}`); process.exit(2); }
const cfg = JSON.parse(block[1]);
const mode = cfg.mode ?? 'content';
const days = Number(opt('days', cfg.trendDays ?? 90));

const defaultExcludes = ['**/node_modules/**', '**/.next/**', '**/dist/**', '**/build/**', '**/coverage/**', '**/*.min.js'];
const includes = (cfg.candidates?.include ?? ['**']).map(globToRegex);
const excludes = [...(cfg.candidates?.noDefaultExcludes ? [] : defaultExcludes), ...(cfg.candidates?.exclude ?? [])].map(globToRegex);
const variants = cfg.variants.map((v) => ({ name: v.name, res: v.any.map((s) => new RegExp(s, v.flags ?? 'm')) }));

// --- candidates and classification ---------------------------------------------
const files = git('ls-files', '-z').split('\0').filter(Boolean)
  .filter((f) => includes.some((r) => r.test(f)) && !excludes.some((r) => r.test(f)))
  .sort();

const notes = [];
let skippedBig = 0;
let unreadable = 0;
const rows = [];
for (const f of files) {
  const hits = {};
  if (mode === 'path') {
    for (const v of variants) if (v.res.some((r) => r.test(f))) hits[v.name] = 1;
  } else {
    let text;
    try {
      const full = join(repo, f);
      if (statSync(full).size > 1_000_000) { skippedBig++; continue; }
      text = readFileSync(full, 'utf8');
    } catch { unreadable++; continue; }
    for (const v of variants) {
      for (const r of v.res) {
        const m = r.exec(text);
        if (m) { hits[v.name] = text.slice(0, m.index).split('\n').length; break; }
      }
    }
  }
  const names = Object.keys(hits).sort();
  rows.push({ file: f, cls: names.length ? names.join('+') : 'none', line: names.length ? Math.min(...names.map((n) => hits[n])) : 0 });
}
if (skippedBig) notes.push(`${skippedBig} file(s) over 1 MB skipped`);
if (unreadable) notes.push(`${unreadable} file(s) unreadable and skipped`);

// --- trend from git history ------------------------------------------------------
const names = (s) => new Set(s.split(/[\0\n]/).filter(Boolean));
// The window ends at the latest commit, not at today, so a quiet repo still has a trend.
const headEpoch = Number(git('log', '-1', '--format=%ct').trim());
const since = String(headEpoch - days * 86400);
const headDate = new Date(headEpoch * 1000).toISOString().slice(0, 10);
const added = names(git('log', `--since=${since}`, '--diff-filter=A', '--name-only', '--format=', '--relative', '-z'));
const touched = names(git('log', `--since=${since}`, '--diff-filter=AM', '--name-only', '--format=', '--relative', '-z'));
if (git('rev-parse', '--is-shallow-repository').trim() === 'true') notes.push('shallow clone: trend is incomplete');
const dirty = git('status', '--porcelain', '--', '.').trim();
if (dirty) notes.push(`working tree not clean (${dirty.split('\n').length} path(s)); content was read from the working tree, history from HEAD`);

// --- aggregate ---------------------------------------------------------------------------
const classes = new Map();
for (const r of rows) {
  const c = classes.get(r.cls) ?? { files: [], added: 0, touched: 0 };
  c.files.push(r);
  if (added.has(r.file)) c.added++;
  if (touched.has(r.file)) c.touched++;
  classes.set(r.cls, c);
}
const matchedRows = rows.filter((r) => r.cls !== 'none');
const ordered = [...classes.entries()].sort((a, b) => b[1].files.length - a[1].files.length || a[0].localeCompare(b[0]));
const matchedClasses = ordered.filter(([k]) => k !== 'none');
const dominant = matchedClasses[0]?.[0] ?? 'n/a';
const addedTotal = matchedClasses.reduce((n, [, c]) => n + c.added, 0);
const addedTop = [...matchedClasses].sort((a, b) => b[1].added - a[1].added || a[0].localeCompare(b[0]))[0];
const dominantAdded = addedTotal > 0 ? addedTop[0] : 'n/a';
const pct = (n, d) => (d ? `${Math.round((n / d) * 100)}%` : 'n/a');
if (matchedRows.length >= 10 && addedTotal / matchedRows.length >= 0.9) {
  notes.push('90% or more of matched files were added inside the window, so history may be a bulk import and the trend is weak');
}

const outliers = dominant === 'n/a' ? [] : matchedRows.filter((r) => r.cls !== dominant);
mkdirSync(join(out, 'reports'), { recursive: true });
mkdirSync(join(out, 'evidence'), { recursive: true });
writeFileSync(join(out, 'evidence', `${id}-files.tsv`),
  ['file\tclass\tline\tadded_in_window\ttouched_in_window',
    ...rows.map((r) => `${r.file}\t${r.cls}\t${r.line}\t${added.has(r.file) ? 'yes' : 'no'}\t${touched.has(r.file) ? 'yes' : 'no'}`)].join('\n') + '\n');
writeFileSync(join(out, 'evidence', `${id}-outliers.txt`),
  outliers.map((r) => `${r.file}:${r.line}\t${r.cls}`).join('\n') + (outliers.length ? '\n' : ''));

// --- write the report --------------------------------------------------------------------
const sha = git('rev-parse', 'HEAD').trim();
const script = relative(process.cwd(), process.argv[1]) || process.argv[1];
const cap = (list, n) => list.slice(0, n);
const L = [];
L.push('---', `probe: ${id}`, `question: ${question}`, 'status: needs-interpretation', 'confidence: unset',
  `repo_sha: ${sha}`, `generated: ${new Date().toISOString()}`, '---', '', `# Probe report: ${id}`, '');
L.push('## Method',
  `- \`node ${script} --probe ${probePath} --repo ${repo} --out ${out} --days ${days}\``,
  `- Candidates: \`git -C ${repo} ls-files\` filtered by the include and exclude globs in the probe file`,
  `- Mode: ${mode}. Variant patterns are in the probe file, section Measure.`,
  `- Trend: \`git log --since=${since} --diff-filter=A --relative --name-only\` (added) and \`--diff-filter=AM\` (touched). ${since} is ${days} days before the latest commit (${headDate}).`,
  ...notes.map((n) => `- Note: ${n}`), '');
L.push('## Population',
  `- candidates: ${rows.length}`,
  `- matched at least one variant: ${matchedRows.length}`,
  `- matched none: ${rows.length - matchedRows.length}`, '');
L.push('## Distribution', '| Variant | Files | Share of matched |', '|---|---|---|',
  ...cap(ordered, 12).map(([k, c]) => `| ${k} | ${c.files.length} | ${k === 'none' ? 'n/a' : pct(c.files.length, matchedRows.length)} |`),
  ...(ordered.length > 12 ? [`| (+${ordered.length - 12} more) | | see evidence/${id}-files.tsv |`] : []), '');
L.push(`## Trend`, `Window: ${days} days ending at the latest commit (${headDate}).`, '| Variant | Files | Added in window | Touched in window | Share of additions |', '|---|---|---|---|---|',
  ...cap(matchedClasses, 12).map(([k, c]) => `| ${k} | ${c.files.length} | ${c.added} | ${c.touched} | ${pct(c.added, addedTotal)} |`),
  `- dominant overall: ${dominant}`, `- dominant among additions: ${dominantAdded}`,
  `- divergent: ${addedTotal >= 5 && dominant !== dominantAdded ? 'yes' : 'no'}${addedTotal < 5 ? ' (fewer than 5 additions, too few to judge)' : ''}`, '');
L.push('## Exemplars',
  ...(cap(matchedClasses, 6).map(([k, c]) => `- ${k}: ${cap(c.files, 3).map((r) => `\`${r.file}:${r.line}\``).join(', ')}`)), '');
L.push('## Outliers', `- count: ${outliers.length} (matched files outside the dominant variant)`, `- full list: evidence/${id}-outliers.txt`,
  ...cap(outliers, 10).map((r) => `- \`${r.file}:${r.line}\` ${r.cls}`), '');
L.push('## Interpretation', 'TODO: agent judgment goes here (max 1200 characters). Say what the facts above mean, not what they are.', '');
L.push('## Unknowns', 'TODO: list what this probe could not determine, or write "None".', '');

writeFileSync(join(out, 'reports', `${id}.md`), L.join('\n'));
console.log(`${id}: ${rows.length} candidates, ${matchedRows.length} matched, dominant=${dominant}, dominant among additions=${dominantAdded}`);
