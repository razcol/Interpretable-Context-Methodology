import esbuild from "esbuild";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dir = path.dirname(fileURLToPath(import.meta.url));
const outfile = path.join(dir, "vendor", "excalidraw-bundle.mjs");

await mkdir(path.dirname(outfile), { recursive: true });

await esbuild.build({
  entryPoints: [path.join(dir, "excalidraw-entry.mjs")],
  bundle: true,
  platform: "node",
  format: "esm",
  outfile,
  loader: {
    ".css": "empty",
    ".woff": "empty",
    ".woff2": "empty",
    ".ttf": "empty",
  },
  external: ["jsdom", "canvas"],
  logLevel: "warning",
});

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log(outfile);
}
