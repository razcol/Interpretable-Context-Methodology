// Usage: node scripts/diff.js --baseline A.png --current B.png [--out DIFF.png] [--threshold 0.1]
//        [--max-diff-ratio 0] [--init] [--fail-on-diff]
// match=true when diffPixels/totalPixels <= max-diff-ratio. Different image sizes never match.
// --init copies current to baseline when the baseline does not exist yet (first run).
// Exit 0 whether or not images match, unless --fail-on-diff (then exit 10 on mismatch).
import fs from 'node:fs';
import path from 'node:path';
import pngjs from 'pngjs';
import pixelmatch from 'pixelmatch';
import { parseArgs, run, CliError, EXIT, ensureDir, fileInfo } from './lib.js';

const { PNG } = pngjs;

function readPng(file, label) {
  if (!fs.existsSync(file)) throw new CliError('FILE_NOT_FOUND', `${label} not found: ${file}`, EXIT.USAGE);
  try {
    return PNG.sync.read(fs.readFileSync(file));
  } catch (e) {
    throw new CliError('BAD_IMAGE', `${label} is not a valid PNG: ${e.message}`, EXIT.USAGE);
  }
}

run(async () => {
  const args = parseArgs(process.argv.slice(2), {
    strings: ['baseline', 'current', 'out', 'threshold', 'max-diff-ratio'],
    booleans: ['init', 'fail-on-diff'],
    required: ['baseline', 'current'],
  });
  const threshold = args.threshold !== undefined ? Number(args.threshold) : 0.1;
  const maxRatio = args.maxDiffRatio !== undefined ? Number(args.maxDiffRatio) : 0;
  if (!(threshold >= 0 && threshold <= 1) || !(maxRatio >= 0 && maxRatio <= 1)) {
    throw new CliError('USAGE', '--threshold and --max-diff-ratio must be between 0 and 1', EXIT.USAGE);
  }
  const current = path.resolve(args.current);
  const baseline = path.resolve(args.baseline);
  if (!fs.existsSync(baseline) && args.init) {
    readPng(current, 'current');
    ensureDir(path.dirname(baseline));
    fs.copyFileSync(current, baseline);
    return { match: true, initialized: true, baseline: fileInfo(baseline) };
  }
  const a = readPng(baseline, 'baseline');
  const b = readPng(current, 'current');
  const base = { baseline, current, threshold, maxDiffRatio: maxRatio };

  let result;
  if (a.width !== b.width || a.height !== b.height) {
    result = { ...base, match: false, reason: 'size-mismatch', baselineSize: `${a.width}x${a.height}`, currentSize: `${b.width}x${b.height}` };
  } else {
    const diff = new PNG({ width: a.width, height: a.height });
    const diffPixels = pixelmatch(a.data, b.data, diff.data, a.width, a.height, { threshold });
    const total = a.width * a.height;
    const ratio = diffPixels / total;
    const out = path.resolve(args.out || path.join(path.dirname(current), `${path.basename(current, '.png')}__diff.png`));
    ensureDir(path.dirname(out));
    if (diffPixels > 0) fs.writeFileSync(out, PNG.sync.write(diff));
    result = {
      ...base,
      match: ratio <= maxRatio,
      diffPixels,
      totalPixels: total,
      diffRatio: Number(ratio.toFixed(6)),
      ...(diffPixels > 0 ? { diffImage: fileInfo(out) } : {}),
    };
  }
  if (!result.match && args.failOnDiff) {
    throw new CliError('DIFF_DETECTED', `Images differ (${result.reason || `ratio ${result.diffRatio} > ${maxRatio}`})`, EXIT.DIFF, result);
  }
  return result;
});
