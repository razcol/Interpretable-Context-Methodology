---
name: system-flowcharts
description: "Plan and generate a detailed editable Excalidraw flowchart for an idea or an existing system. Use when the user wants a flowchart, process diagram, decision flow, or a picture of how a system works. Not for wireframes, freeform sketches, or sequence diagrams."
status: active (approved 2026-10-28, tested on the skill-factory pipeline, an order-fulfillment flow, and the figma-section-fields pipeline)
license: N/A (internal)
---

# System flowcharts

The agent decides what the chart says. A script decides where the shapes go and how arrows attach. The file is an editable `.excalidraw` document.

Excalidraw is the tool. It is MIT-licensed, opens on excalidraw.com and in the VS Code or Cursor extension, and the generator runs in Node without a browser. tldraw's SDK is licensed for development use only and needs a headless browser to build a `.tldr` file, so it is not the generator.

## Setup

Once per machine, from this skill folder:

```bash
npm install
```

Requires Node 22 or newer. The install builds a local bundle of `@excalidraw/excalidraw@0.18.1`. Do not upgrade those packages inside a charting task.

## Before drawing

Read `references/planning.md` and plan the chart from it. Keep that plan in the conversation. Do not write a `planning.md`.

Then write a spec outside the output folder. A temp file is the right place. The schema is `references/spec.md`. A worked example is `references/example-skill-factory.flow.json`.

Do not put coordinates in the spec. Do not draw the chart by hand as Excalidraw JSON.

## Generate

From this skill folder:

```bash
node scripts/build-flowchart.mjs path/to/spec.json --out path/to/name.excalidraw
```

When the user already has a Mermaid `flowchart`, or a spec run left overlapping frames:

```bash
node scripts/build-flowchart.mjs --mermaid path/to/flow.mmd --out path/to/name.excalidraw
```

The script writes `name.png` beside the `.excalidraw` file and nothing else. Read the PNG. If a label sits off its arrow, a frame covers a node from another group, or two arrows cross in a way that hides the story, change the spec (shorter labels, fewer nodes, drop or split `groups`) and run the script again. Never patch `x`, `y`, or `points` in the output.

Delete the spec after a successful run. Do not leave a planning note, a spec, a Mermaid file, or an SVG in the output folder.

Stdout is one JSON object. `ok: true` means the file passed the binding and overlap checks.

| Exit | Meaning |
|------|---------|
| 0 | File written and checks passed |
| 1 | Bad arguments |
| 2 | Spec or Mermaid input failed validation |
| 3 | Layout or conversion failed |
| 4 | File was written, then failed the binding or overlap check |

## After drawing

Write a reading guide of a few sentences: where to start, what each group is for, and which path is the usual one. Point the user at the `.excalidraw` file and the `.png`. Those two files are the whole result.

## What the two inputs are for

| Input | Use it when |
|-------|-------------|
| Spec JSON | This is the default. Decisions, start/end, input/output, storage, and errors keep their shapes and colors. |
| Mermaid flowchart | The user already has Mermaid, or grouped phases lay out more clearly as `subgraph` blocks. Cylinders and parallelograms become colored rectangles. Subgraphs become rectangles, not Excalidraw frames. |

## Shape colors

| Kind | Looks like | Fill | Stroke |
|------|------------|------|--------|
| `start`, `end` | Green ellipse | `#d3f9d8` | `#2b8a3e` |
| `error` | Red ellipse | `#ffe3e3` | `#c92a2a` |
| `process` | Blue rounded rectangle | `#d0ebff` | `#1971c2` |
| `decision` | Yellow diamond | `#fff3bf` | `#e67700` |
| `io` | Orange rectangle | `#ffe8cc` | `#d9480f` |
| `storage` | Purple dashed rounded rectangle | `#e5dbff` | `#6741d9` |
| `subprocess` | Blue rectangle, thick stroke | `#e7f5ff` | `#1864ab` |

Excalidraw has no cylinder or parallelogram. Storage and input/output use these rectangles on purpose.

## Rules the script already enforces

- One reading direction. Default `DOWN` (top to bottom). `RIGHT` only when the user asks for a left-to-right chart.
- Every decision is a question and has at least two labeled branches.
- No self-loops. Add a named step instead.
- At most 36 nodes. Split a larger system into more than one chart.
- Arrow endpoints stay bound to shapes, so a later drag in Excalidraw does not leave a floating arrow.
- A long top-to-bottom chart may continue in a second column on the right. Read the left column first, then follow the arrow into the right column. That continuation is intentional.
- The same spec produces the same file bytes.
