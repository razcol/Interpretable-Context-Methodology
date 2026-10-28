import { createRequire } from "node:module";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { installDomShim } from "./dom-shim.mjs";

const require = createRequire(import.meta.url);
const ELK = require("elkjs/lib/elk.bundled.js");
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const bundlePath = path.join(scriptDir, "vendor", "excalidraw-bundle.mjs");

const FONT_SIZE = 18;
const FONT_FAMILY = 2;
const CHAR_RATIO = 0.55;
const LINE_HEIGHT = 1.25;
const MAX_NODES = 36;
const ID_RE = /^[A-Za-z][A-Za-z0-9_-]{0,40}$/;

const KINDS = {
  start: { type: "ellipse", backgroundColor: "#b2f2bb", roundness: { type: 2 } },
  end: { type: "ellipse", backgroundColor: "#b2f2bb", roundness: { type: 2 } },
  error: { type: "ellipse", backgroundColor: "#ffc9c9", roundness: { type: 2 } },
  process: { type: "rectangle", backgroundColor: "#a5d8ff", roundness: { type: 3 } },
  decision: { type: "diamond", backgroundColor: "#ffec99", roundness: null },
  io: { type: "rectangle", backgroundColor: "#ffd8a8", roundness: null },
  storage: {
    type: "rectangle",
    backgroundColor: "#d0bfff",
    roundness: { type: 3 },
    strokeStyle: "dashed",
  },
  subprocess: {
    type: "rectangle",
    backgroundColor: "#d0ebff",
    roundness: { type: 3 },
    strokeWidth: 4,
  },
};

class SkillError extends Error {
  constructor(code, message, details) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

function fail(code, message, details) {
  throw new SkillError(code, message, details);
}

function usage() {
  return [
    "Usage:",
    "  node scripts/build-flowchart.mjs <spec.json> --out <file.excalidraw>",
    "  node scripts/build-flowchart.mjs --mermaid <file.mmd> --out <file.excalidraw>",
    "",
    "Writes the .excalidraw file and a sibling .svg. Prints one JSON object.",
  ].join("\n");
}

function parseArgs(argv) {
  const args = { positional: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--out") args.out = argv[++i];
    else if (token === "--mermaid") args.mermaid = argv[++i];
    else if (token === "--help" || token === "-h") args.help = true;
    else if (token.startsWith("--")) fail(1, `Unknown argument: ${token}`);
    else args.positional.push(token);
  }
  return args;
}

function hashSeed(id) {
  let hash = 2166136261;
  for (const char of id) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  return (hash >>> 0) % 2147483646 || 1;
}

function wrapLabel(label, maxChars) {
  const words = String(label).trim().split(/\s+/);
  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > maxChars && current) {
      lines.push(current);
      current = word;
    } else current = next;
  }
  if (current) lines.push(current);
  return lines.length ? lines : [""];
}

function measure(lines) {
  const longest = Math.max(...lines.map((line) => [...line].length), 1);
  return {
    textW: longest * FONT_SIZE * CHAR_RATIO,
    textH: lines.length * FONT_SIZE * LINE_HEIGHT,
  };
}

function sizeNode(node) {
  const maxChars = node.kind === "decision" ? 16 : 22;
  const lines = wrapLabel(node.label, maxChars);
  const { textW, textH } = measure(lines);
  let width;
  let height;
  if (node.kind === "decision") {
    width = Math.max(210, Math.ceil(textW * 2.2));
    height = Math.max(140, Math.ceil(textH * 2.6));
  } else if (node.kind === "start" || node.kind === "end" || node.kind === "error") {
    width = Math.max(180, Math.ceil(textW + 64));
    height = Math.max(68, Math.ceil(textH + 36));
  } else {
    width = Math.max(190, Math.ceil(textW + 56));
    height = Math.max(76, Math.ceil(textH + 40));
  }
  return { text: lines.join("\n"), width, height };
}

function directionOf(spec) {
  const value = String(spec.direction || "DOWN").toUpperCase();
  if (value === "RIGHT" || value === "LR") return "RIGHT";
  if (value === "DOWN" || value === "TB") return "DOWN";
  fail(2, `direction must be DOWN or RIGHT, got ${spec.direction}`);
}

function validateSpec(spec) {
  if (!spec || typeof spec !== "object" || Array.isArray(spec)) fail(2, "Spec must be a JSON object.");
  if (!Array.isArray(spec.nodes) || spec.nodes.length === 0) fail(2, "Spec needs a nodes array.");
  if (!Array.isArray(spec.edges) || spec.edges.length === 0) fail(2, "Spec needs an edges array.");
  if (spec.nodes.length > MAX_NODES) {
    fail(2, `Spec has ${spec.nodes.length} nodes. Split the chart so each file stays under ${MAX_NODES}.`);
  }

  const problems = [];
  const ids = new Set();
  for (const node of spec.nodes) {
    if (!node || !ID_RE.test(node.id || "")) problems.push(`Bad node id: ${JSON.stringify(node?.id)}`);
    else if (ids.has(node.id)) problems.push(`Duplicate node id: ${node.id}`);
    else ids.add(node.id);
    if (!KINDS[node.kind]) problems.push(`Node ${node.id || "?"} has unknown kind ${JSON.stringify(node.kind)}`);
    if (!node.label || !String(node.label).trim()) problems.push(`Node ${node.id || "?"} needs a label`);
    if (node.kind === "decision" && !String(node.label || "").trim().endsWith("?")) {
      problems.push(`Decision ${node.id} must be a question ending in ?`);
    }
  }

  spec.edges.forEach((edge, index) => {
    if (!ids.has(edge?.from)) problems.push(`Edge ${index + 1} starts at unknown node ${JSON.stringify(edge?.from)}`);
    if (!ids.has(edge?.to)) problems.push(`Edge ${index + 1} ends at unknown node ${JSON.stringify(edge?.to)}`);
    if (edge?.from && edge.from === edge.to) {
      problems.push(`Edge ${edge.from} loops to itself. Add a named step instead of a self-loop.`);
    }
  });

  const groups = spec.groups || [];
  if (!Array.isArray(groups)) problems.push("groups must be an array");
  const grouped = new Map();
  for (const group of groups) {
    if (!group || !ID_RE.test(group.id || "")) problems.push(`Bad group id: ${JSON.stringify(group?.id)}`);
    if (ids.has(group?.id)) problems.push(`Group id ${group.id} collides with a node id`);
    if (!group?.label || !String(group.label).trim()) problems.push(`Group ${group?.id || "?"} needs a label`);
    if (!Array.isArray(group?.nodeIds) || group.nodeIds.length === 0) {
      problems.push(`Group ${group?.id || "?"} needs nodeIds`);
    }
    for (const nodeId of group?.nodeIds || []) {
      if (!ids.has(nodeId)) problems.push(`Group ${group.id} lists unknown node ${nodeId}`);
      else if (grouped.has(nodeId)) problems.push(`Node ${nodeId} is in more than one group`);
      else grouped.set(nodeId, group.id);
    }
  }

  const outgoing = new Map();
  for (const edge of spec.edges) {
    if (!edge?.from) continue;
    const list = outgoing.get(edge.from) || [];
    list.push(edge);
    outgoing.set(edge.from, list);
  }
  for (const node of spec.nodes) {
    if (node.kind !== "decision") continue;
    const branches = outgoing.get(node.id) || [];
    if (branches.length < 2) problems.push(`Decision ${node.id} needs at least two outgoing edges`);
    for (const branch of branches) {
      if (!branch.label || !String(branch.label).trim()) {
        problems.push(`Decision ${node.id} has an unlabeled branch to ${branch.to}`);
      }
    }
  }

  const hasStart = spec.nodes.some((node) => node.kind === "start");
  const hasEnd = spec.nodes.some((node) => node.kind === "end" || node.kind === "error");
  if (!hasStart) problems.push("Add a start node");
  if (!hasEnd) problems.push("Add an end node");

  if (problems.length) fail(2, "Spec failed validation", problems);
  return { ids, grouped };
}

function elkNode(node, sized) {
  return { id: node.id, width: sized.width, height: sized.height };
}

async function layoutSpec(spec) {
  const direction = directionOf(spec);
  const sized = new Map(spec.nodes.map((node) => [node.id, sizeNode(node)]));
  // Groups become frames after layout. Compound ELK nodes pulled external
  // steps beside a whole phase instead of keeping one reading direction.
  const graph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": direction,
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.spacing.nodeNode": "64",
      "elk.layered.spacing.nodeNodeBetweenLayers": "110",
      "elk.spacing.edgeNode": "40",
      "elk.layered.spacing.edgeNodeBetweenLayers": "40",
      "elk.spacing.edgeEdge": "28",
      "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
      "elk.padding": "[top=32,left=32,bottom=32,right=32]",
      "elk.layered.cycleBreaking.strategy": "MODEL_ORDER",
      "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
      "elk.separateConnectedComponents": "false",
    },
    children: spec.nodes.map((node) => elkNode(node, sized.get(node.id))),
    edges: spec.edges.map((edge, index) => ({
      id: `${edge.from}__${edge.to}__${index}`,
      sources: [edge.from],
      targets: [edge.to],
    })),
  };

  const elk = new ELK();
  const laidOut = await elk.layout(graph);
  return { laidOut, sized, direction };
}

function absoluteNodes(layout) {
  const nodes = new Map();
  const walk = (node, originX, originY) => {
    const x = originX + (node.x || 0);
    const y = originY + (node.y || 0);
    nodes.set(node.id, { ...node, absX: x, absY: y });
    for (const child of node.children || []) walk(child, x, y);
  };
  walk(layout, 0, 0);
  return nodes;
}

function routeOf(edge) {
  const points = [];
  const add = (point) => {
    if (!point) return;
    const last = points.at(-1);
    if (last && last.x === point.x && last.y === point.y) return;
    points.push({ x: point.x, y: point.y });
  };
  for (const section of edge.sections || []) {
    add(section.startPoint);
    for (const bend of section.bendPoints || []) add(bend);
    add(section.endPoint);
  }
  if (points.length < 2) return null;
  const origin = points[0];
  return {
    x: origin.x,
    y: origin.y,
    points: points.map((point) => [point.x - origin.x, point.y - origin.y]),
  };
}

function skeletonsFromSpec(spec, layout) {
  const positions = absoluteNodes(layout.laidOut);
  const shapes = [];
  for (const node of spec.nodes) {
    const place = positions.get(node.id);
    const box = layout.sized.get(node.id);
    const kind = node.tone === "error" && node.kind === "end" ? KINDS.error : KINDS[node.kind];
    shapes.push({
      id: node.id,
      type: kind.type,
      x: place.absX,
      y: place.absY,
      width: box.width,
      height: box.height,
      backgroundColor: kind.backgroundColor,
      strokeColor: "#1e1e1e",
      fillStyle: "solid",
      strokeWidth: kind.strokeWidth || 2,
      strokeStyle: kind.strokeStyle || "solid",
      roughness: 0,
      opacity: 100,
      roundness: kind.roundness,
      label: {
        text: box.text,
        fontSize: FONT_SIZE,
        fontFamily: FONT_FAMILY,
        strokeColor: "#1e1e1e",
      },
    });
  }

  const arrows = spec.edges.map((edge, index) => {
    const id = `${edge.from}__${edge.to}__${index}`;
    const laid = (layout.laidOut.edges || []).find((item) => item.id === id);
    const route = laid ? routeOf(laid) : null;
    const arrow = {
      id,
      type: "arrow",
      strokeColor: "#1e1e1e",
      strokeWidth: 2,
      roughness: 0,
      endArrowhead: "arrow",
      startArrowhead: null,
      elbowed: false,
      start: { id: edge.from },
      end: { id: edge.to },
    };
    if (route) {
      arrow.x = route.x;
      arrow.y = route.y;
      arrow.points = route.points;
    }
    if (edge.label && String(edge.label).trim()) {
      arrow.label = {
        text: String(edge.label).trim(),
        fontSize: 16,
        fontFamily: FONT_FAMILY,
        strokeColor: "#1e1e1e",
      };
    }
    return arrow;
  });

  const frames = (spec.groups || []).map((group) => {
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const nodeId of group.nodeIds) {
      const place = positions.get(nodeId);
      const box = layout.sized.get(nodeId);
      minX = Math.min(minX, place.absX);
      minY = Math.min(minY, place.absY);
      maxX = Math.max(maxX, place.absX + box.width);
      maxY = Math.max(maxY, place.absY + box.height);
    }
    const padX = 36;
    const padTop = 56;
    const padBottom = 32;
    return {
      id: group.id,
      type: "frame",
      name: group.label,
      x: minX - padX,
      y: minY - padTop,
      width: maxX - minX + padX * 2,
      height: maxY - minY + padTop + padBottom,
      children: group.nodeIds,
    };
  });

  return [...shapes, ...arrows, ...frames];
}

function normLabel(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function scanMermaidKinds(definition) {
  const kinds = new Map();
  const token =
    /[A-Za-z][\w-]*(?:\(\[([^[\]]+?)\]\)|\[\/([^[\]]+?)\/\]|\[\(([^[\]]+?)\)\]|\[\[([^[\]]+?)\]\]|\{([^{}]+?)\}|\[([^[\]]+?)\])/g;
  const kindByGroup = ["start", "io", "storage", "subprocess", "decision", "process"];
  for (const rawLine of definition.split(/\n/)) {
    const line = rawLine.replace(/%%.*$/, "");
    for (const match of line.matchAll(token)) {
      const groupIndex = match.slice(1).findIndex(Boolean);
      if (groupIndex < 0) continue;
      kinds.set(normLabel(match[groupIndex + 1].replace(/<br\s*\/?>/gi, " ")), kindByGroup[groupIndex]);
    }
  }
  return kinds;
}

function recolorByLabel(elements, kinds) {
  const byId = new Map(elements.map((element) => [element.id, element]));
  let downgraded = 0;
  for (const element of elements) {
    if (element.type !== "text" || !element.containerId) continue;
    const kindName = kinds.get(normLabel(element.text));
    if (!kindName) continue;
    const container = byId.get(element.containerId);
    if (!container || container.type === "arrow") continue;
    const kind = KINDS[kindName];
    if (kindName === "storage" || kindName === "io") downgraded += 1;
    if (kindName === "start") {
      container.type = "ellipse";
      container.roundness = { type: 2 };
    }
    container.backgroundColor = kind.backgroundColor;
    container.fillStyle = "solid";
    container.roughness = 0;
    container.strokeStyle = kind.strokeStyle || "solid";
    if (kind.strokeWidth) container.strokeWidth = kind.strokeWidth;
  }
  return downgraded;
}

function unclipConnectors(elements) {
  const arrows = new Set(elements.filter((element) => element.type === "arrow").map((element) => element.id));
  for (const element of elements) {
    if (element.type === "arrow") element.frameId = null;
    if (element.type === "text" && arrows.has(element.containerId)) element.frameId = null;
  }
}

function stabilize(elements) {
  const renames = new Map();
  const used = new Set(elements.map((element) => element.id));
  for (const element of elements) {
    if (element.type !== "text" || !element.containerId) continue;
    let next = `${element.containerId}__label`;
    let suffix = 2;
    while (used.has(next) && renames.get(element.id) !== next) {
      next = `${element.containerId}__label_${suffix}`;
      suffix += 1;
    }
    used.add(next);
    renames.set(element.id, next);
  }
  for (const element of elements) {
    if (renames.has(element.id)) element.id = renames.get(element.id);
    for (const bound of element.boundElements || []) {
      if (renames.has(bound.id)) bound.id = renames.get(bound.id);
    }
    if (Array.isArray(element.boundElements)) {
      element.boundElements.sort((a, b) => `${a.type}:${a.id}`.localeCompare(`${b.type}:${b.id}`));
    }
    const seed = hashSeed(element.id || "element");
    element.seed = seed;
    element.versionNonce = seed;
    element.updated = 1;
    element.version = 1;
  }
  return elements;
}

function applyRoutes(elements, spec, layout) {
  const byId = new Map(elements.map((element) => [element.id, element]));
  spec.edges.forEach((edge, index) => {
    const id = `${edge.from}__${edge.to}__${index}`;
    const arrow = byId.get(id);
    const laid = (layout.laidOut.edges || []).find((item) => item.id === id);
    const route = laid ? routeOf(laid) : null;
    if (!arrow || !route) return;
    const xs = route.points.map((point) => point[0]);
    const ys = route.points.map((point) => point[1]);
    arrow.x = route.x;
    arrow.y = route.y;
    arrow.points = route.points;
    arrow.width = Math.max(...xs) - Math.min(...xs);
    arrow.height = Math.max(...ys) - Math.min(...ys);
    arrow.elbowed = false;
  });
  placeArrowLabels(elements);
}

function placeArrowLabels(elements) {
  const byId = new Map(elements.map((element) => [element.id, element]));
  for (const element of elements) {
    if (element.type !== "text" || !element.containerId) continue;
    const arrow = byId.get(element.containerId);
    if (!arrow || arrow.type !== "arrow" || !Array.isArray(arrow.points) || arrow.points.length < 2) continue;
    let best = null;
    for (let index = 0; index < arrow.points.length - 1; index += 1) {
      const [x1, y1] = arrow.points[index];
      const [x2, y2] = arrow.points[index + 1];
      const len = Math.hypot(x2 - x1, y2 - y1);
      if (!best || len > best.len) best = { len, x1, y1, x2, y2 };
    }
    if (!best || best.len < 20) continue;
    const midX = arrow.x + (best.x1 + best.x2) / 2;
    const midY = arrow.y + (best.y1 + best.y2) / 2;
    const vertical = Math.abs(best.x2 - best.x1) < Math.abs(best.y2 - best.y1);
    if (vertical) {
      element.x = midX + 12;
      element.y = midY - element.height / 2;
    } else {
      element.x = midX - element.width / 2;
      element.y = midY - element.height - 8;
    }
  }
}

function checkElements(elements) {
  const problems = [];
  const byId = new Map(elements.map((element) => [element.id, element]));
  const shapes = elements.filter((element) =>
    ["rectangle", "diamond", "ellipse"].includes(element.type) && !element.isDeleted,
  );

  for (const element of elements) {
    if (element.isDeleted) continue;
    if (element.type === "arrow") {
      const start = element.startBinding?.elementId;
      const end = element.endBinding?.elementId;
      if (!start || !end || !byId.has(start) || !byId.has(end)) {
        problems.push(`Arrow ${element.id} is missing a binding`);
      } else {
        for (const [ownerId, bindingId] of [[start, element.id], [end, element.id]]) {
          const owner = byId.get(ownerId);
          const listed = (owner.boundElements || []).some((item) => item.id === bindingId);
          if (!listed) problems.push(`Node ${ownerId} does not list arrow ${element.id}`);
        }
      }
    }
    if (element.containerId && !byId.has(element.containerId)) {
      problems.push(`Text ${element.id} points at missing container ${element.containerId}`);
    }
    for (const bound of element.boundElements || []) {
      if (!byId.has(bound.id)) problems.push(`${element.id} lists missing element ${bound.id}`);
    }
  }

  for (let i = 0; i < shapes.length; i += 1) {
    for (let j = i + 1; j < shapes.length; j += 1) {
      const a = shapes[i];
      const b = shapes[j];
      const contains = (outer, inner) =>
      inner.x >= outer.x - 1 &&
      inner.y >= outer.y - 1 &&
      inner.x + inner.width <= outer.x + outer.width + 1 &&
      inner.y + inner.height <= outer.y + outer.height + 1;
    if (contains(a, b) || contains(b, a)) continue;
    const separated =
      a.x + a.width <= b.x + 2 ||
      b.x + b.width <= a.x + 2 ||
      a.y + a.height <= b.y + 2 ||
      b.y + b.height <= a.y + 2;
    if (!separated) problems.push(`Nodes ${a.id} and ${b.id} overlap`);
    }
  }
  return problems;
}

async function loadExcalidraw() {
  try {
    await access(bundlePath);
  } catch {
    await import("./bundle-runtime.mjs");
  }
  installDomShim();
  return import(bundlePath);
}

async function writeDiagram(elements, outFile, warnings) {
  const excalidraw = await loadExcalidraw();
  unclipConnectors(elements);
  const stabilized = stabilize(elements);
  const problems = checkElements(stabilized);
  const appState = {
    viewBackgroundColor: "#ffffff",
    exportBackground: true,
    exportWithDarkMode: false,
    gridSize: 20,
  };
  const parsed = JSON.parse(excalidraw.serializeAsJSON(stabilized, appState, {}, "local"));
  parsed.source = "https://excalidraw.com";
  const json = JSON.stringify(parsed, null, 2);
  await mkdir(path.dirname(outFile), { recursive: true });
  await writeFile(outFile, `${json}\n`);

  const svgFile = outFile.replace(/\.excalidraw$/i, "") + ".svg";
  const svg = await excalidraw.exportToSvg({
    elements: stabilized.filter((element) => !element.isDeleted),
    appState,
    files: null,
    exportPadding: 24,
    skipInliningFonts: true,
  });
  await writeFile(svgFile, svg.outerHTML);

  let pngFile = null;
  try {
    const { Resvg } = await import("@resvg/resvg-js");
    pngFile = svgFile.replace(/\.svg$/i, ".png");
    const rendered = new Resvg(svg.outerHTML, { fitTo: { mode: "width", value: 1600 } });
    await writeFile(pngFile, rendered.render().asPng());
  } catch (error) {
    warnings.push(`PNG preview was not written: ${error.message}`);
  }

  if (problems.length) fail(4, "Diagram failed the quality check", { problems, out: outFile, svg: svgFile, png: pngFile });
  return { out: outFile, svg: svgFile, png: pngFile, warnings, elements: stabilized.length };
}

async function fromSpec(specPath, outFile) {
  let spec;
  try {
    spec = JSON.parse(await readFile(specPath, "utf8"));
  } catch (error) {
    fail(2, `Could not read spec: ${error.message}`);
  }
  validateSpec(spec);
  const layout = await layoutSpec(spec);
  const excalidraw = await loadExcalidraw();
  const elements = excalidraw.convertToExcalidrawElements(skeletonsFromSpec(spec, layout), {
    regenerateIds: false,
  });
  applyRoutes(elements, spec, layout);
  return writeDiagram(elements, outFile, []);
}

async function fromMermaid(mermaidPath, outFile) {
  const definition = await readFile(mermaidPath, "utf8");
  if (!/flowchart\s+(TD|TB|LR|RL)/i.test(definition)) {
    fail(2, "Mermaid input must be a flowchart TD, TB, LR, or RL diagram.");
  }
  installDomShim();
  const { parseMermaidToExcalidraw } = await import("@excalidraw/mermaid-to-excalidraw");
  let parsed;
  try {
    parsed = await parseMermaidToExcalidraw(definition, {
      flowchart: { curve: "linear" },
      fontSize: FONT_SIZE,
    });
  } catch (error) {
    fail(3, `Mermaid conversion failed: ${error.message}`);
  }
  const excalidraw = await loadExcalidraw();
  const elements = excalidraw.convertToExcalidrawElements(parsed.elements, { regenerateIds: false });
  const downgraded = recolorByLabel(elements, scanMermaidKinds(definition));
  const warnings = [];
  if (downgraded) {
    warnings.push(
      `${downgraded} storage or input/output shape(s) survive only as colored rectangles. Excalidraw has no cylinder or parallelogram.`,
    );
  }
  return writeDiagram(elements, outFile, warnings);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.out || (!args.mermaid && args.positional.length !== 1)) {
    fail(1, usage());
  }
  const outFile = path.resolve(args.out);
  if (!outFile.endsWith(".excalidraw")) fail(1, "--out must end in .excalidraw");
  if (args.mermaid && args.positional.length) fail(1, "Pass either a spec json or --mermaid, not both.");

  const result = args.mermaid
    ? await fromMermaid(path.resolve(args.mermaid), outFile)
    : await fromSpec(path.resolve(args.positional[0]), outFile);

  console.log(JSON.stringify({ ok: true, approach: args.mermaid ? "mermaid" : "elk", ...result }));
}

main().catch((error) => {
  const payload = {
    ok: false,
    error: {
      code: error.code || 3,
      message: error.message,
      details: error.details,
    },
  };
  console.log(JSON.stringify(payload));
  process.exit(Number(error.code) || 3);
});
