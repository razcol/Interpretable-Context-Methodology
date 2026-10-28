import { JSDOM } from "jsdom";

const CHAR_RATIO = 0.55;

export function installDomShim() {
  if (globalThis.__systemFlowchartsDom) return;
  const dom = new JSDOM("<!doctype html><html><body></body></html>", {
    pretendToBeVisual: true,
    url: "http://localhost/",
  });
  const { window } = dom;

  for (const key of Object.getOwnPropertyNames(window)) {
    if (key in globalThis) continue;
    try {
      globalThis[key] = window[key];
    } catch {
      // Some browser globals are not writable. The ones Excalidraw needs are set below.
    }
  }

  globalThis.window = window;
  globalThis.document = window.document;
  globalThis.devicePixelRatio = 1;
  globalThis.FontFace = class FontFace {
    load() {
      return Promise.resolve(this);
    }
  };
  window.FontFace = globalThis.FontFace;
  const fonts = {
    add() {},
    check: () => true,
    load: async () => [],
    ready: Promise.resolve(),
    forEach() {},
  };
  window.document.fonts = fonts;

  const context = new Proxy(
    {
      font: "18px sans-serif",
      filter: "none",
      measureText(text) {
        const size = Number.parseFloat(this.font) || 18;
        const width = [...String(text)].length * size * CHAR_RATIO;
        return {
          width,
          actualBoundingBoxAscent: size * 0.8,
          actualBoundingBoxDescent: size * 0.2,
        };
      },
    },
    {
      get(target, prop) {
        if (prop in target) return target[prop];
        return () => {};
      },
      set(target, prop, value) {
        target[prop] = value;
        return true;
      },
    },
  );

  window.HTMLCanvasElement.prototype.getContext = () => context;
  globalThis.__systemFlowchartsDom = true;
}
