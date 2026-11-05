// Runs esbuild for harness.py. Reads one JSON config on stdin, writes only config.outfile.
// Prints {"ok": true, "stubsHit": [...], "warnings": [...]} on stdout; esbuild errors go to stderr with exit 3.
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

const readStdin = async () => {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8');
};

const config = JSON.parse(await readStdin());
const esbuild = require(config.esbuildPackage);
const hits = new Map();
const fileStubs = config.fileStubs.map((stub) => ({ ...stub, regex: new RegExp(stub.pattern) }));
const STUB_NS = 'harness-stub';

const hit = (name, args) => {
  const entry = hits.get(name) || { module: name, importers: [] };
  const importer = args.importer || '<entry>';
  if (!entry.importers.includes(importer)) entry.importers.push(importer);
  hits.set(name, entry);
};

const stubPlugin = {
  name: 'harness-stubs',
  setup(build) {
    build.onResolve({ filter: /.*/ }, async (args) => {
      if (args.pluginData?.harness || args.namespace === STUB_NS) return undefined;
      if (Object.hasOwn(config.bareStubs, args.path)) {
        hit(args.path, args);
        return { path: args.path, namespace: STUB_NS, pluginData: { source: config.bareStubs[args.path] } };
      }
      if (args.kind === 'entry-point' || args.importer.includes('/node_modules/')) return undefined;
      const resolved = await build.resolve(args.path, {
        kind: args.kind,
        importer: args.importer,
        resolveDir: args.resolveDir,
        namespace: 'file',
        pluginData: { harness: true }
      });
      if (resolved.errors.length || !resolved.path) return undefined;
      if (!resolved.path.startsWith(config.sectionDir)) {
        const stub = fileStubs.find((candidate) => candidate.regex.test(resolved.path));
        if (stub) {
          hit(stub.name, args);
          return { path: stub.name, namespace: STUB_NS, pluginData: { source: stub.source } };
        }
      }
      return { path: resolved.path, namespace: resolved.namespace, external: resolved.external, sideEffects: resolved.sideEffects, suffix: resolved.suffix };
    });
    build.onLoad({ filter: /.*/, namespace: STUB_NS }, (args) => ({
      contents: args.pluginData.source,
      loader: 'jsx',
      resolveDir: config.entry.resolveDir
    }));
  }
};

try {
  const result = await esbuild.build({
    stdin: { contents: config.entry.contents, resolveDir: config.entry.resolveDir, sourcefile: 'harness-entry.jsx', loader: 'jsx' },
    bundle: true,
    outfile: config.outfile,
    format: 'iife',
    platform: 'browser',
    target: 'es2020',
    jsx: 'automatic',
    loader: { '.js': 'jsx' },
    nodePaths: config.nodePaths,
    ...(config.tsconfig ? { tsconfig: config.tsconfig } : {}),
    define: { 'process.env.NODE_ENV': '"production"' },
    banner: { js: 'var process = globalThis.process || { env: {} };' },
    legalComments: 'none',
    logLevel: 'silent',
    plugins: [stubPlugin]
  });
  const warnings = esbuild.formatMessagesSync(result.warnings, { kind: 'warning', color: false });
  process.stdout.write(JSON.stringify({ ok: true, stubsHit: [...hits.values()], warnings }) + '\n');
} catch (error) {
  const messages = error.errors?.length
    ? esbuild.formatMessagesSync(error.errors, { kind: 'error', color: false }).join('')
    : String(error?.stack || error);
  process.stderr.write(messages);
  process.exit(3);
}
