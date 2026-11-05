import path from "node:path";
import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";

/**
 * Put PatternFly's per-component stylesheets into the `patternfly` cascade
 * layer.
 *
 * `@patternfly/react-core` components `import` their own CSS from
 * `@patternfly/react-styles`, and those files ship unlayered. Unlayered CSS
 * beats every layered rule regardless of specificity, so without this the
 * component styles would outrank Tailwind utilities — the exact breakage
 * src/frontend/global.css documents. Wrapping them here keeps the layer
 * order declared in that file meaningful while letting us drop the 2 MB
 * monolithic `patternfly.css`.
 *
 * The target layer is `pf-components`, which global.css orders after `base`:
 * putting it in the bottom `patternfly` layer instead leaves Tailwind's
 * preflight reset on top, which un-styles every PatternFly button and card.
 */
function patternflyLayer(): Plugin {
  return {
    name: "patternfly-cascade-layer",
    enforce: "pre",
    transform(code, id) {
      const file = id.split("?")[0];
      if (!file.endsWith(".css")) return null;
      if (!file.includes("@patternfly/react-styles/css/")) return null;
      return { code: `@layer pf-components {\n${code}\n}`, map: null };
    },
  };
}

/**
 * Write `.br` and `.gz` siblings for every text asset.
 *
 * `@fastify/compress` otherwise compresses on every request, which forces a
 * low brotli quality for latency reasons (q4). Doing it once at build time
 * affords q11 — about 30% smaller on the stylesheet — and costs the server
 * nothing per request, because `@fastify/static` serves the precompressed
 * file directly (`preCompressed: true`).
 */
function precompressAssets(): Plugin {
  return {
    name: "precompress-assets",
    apply: "build",
    enforce: "post",
    async writeBundle(options, bundle) {
      const zlib = await import("node:zlib");
      const fsp = await import("node:fs/promises");
      const { promisify } = await import("node:util");
      const brotli = promisify(zlib.brotliCompress);
      const gzip = promisify(zlib.gzip);
      const outDir = options.dir ?? "dist/frontend";

      await Promise.all(
        Object.keys(bundle)
          .filter((name) => /\.(js|css|svg|json)$/.test(name))
          .map(async (name) => {
            const file = path.join(outDir, name);
            const buf = await fsp.readFile(file);
            if (buf.length < 1024) return;
            const [br, gz] = await Promise.all([
              brotli(buf, {
                params: {
                  [zlib.constants.BROTLI_PARAM_QUALITY]: 11,
                  [zlib.constants.BROTLI_PARAM_SIZE_HINT]: buf.length,
                },
              }),
              gzip(buf, { level: 9 }),
            ]);
            await Promise.all([
              fsp.writeFile(`${file}.br`, br),
              fsp.writeFile(`${file}.gz`, gz),
            ]);
          }),
      );
    },
  };
}

/** Layer precedence, lowest first. Must match the statement in global.css. */
const LAYER_ORDER = "@layer patternfly, theme, base, pf-components, components, utilities;";

/**
 * Re-assert the cascade layer order on the emitted stylesheet.
 *
 * A layer's priority is fixed the first time it is named, so global.css
 * opens with an `@layer a, b, c;` statement. Tailwind v4 processes that file
 * and the statement does not survive into the build output — leaving the
 * order to be inferred from first appearance, which puts `pf-components`
 * below Tailwind's `base` and lets preflight un-style every PatternFly
 * component. Prepending it here is the one place that is guaranteed to run
 * after Tailwind and before the browser.
 */
function cssLayerOrder(): Plugin {
  return {
    name: "css-layer-order",
    enforce: "post",
    generateBundle(_options, bundle) {
      for (const asset of Object.values(bundle)) {
        if (asset.type !== "asset" || !asset.fileName.endsWith(".css")) continue;
        const source = typeof asset.source === "string"
          ? asset.source
          : Buffer.from(asset.source).toString("utf-8");
        if (source.startsWith(LAYER_ORDER)) continue;
        asset.source = `${LAYER_ORDER}\n${source}`;
      }
    },
  };
}

// https://vitejs.dev/config/

// `.env` sets PORT=5003 for the BFF, and vite does not put `.env`
// values on `process.env` — it exposes the `VITE_`-prefixed ones on
// `import.meta.env` and nothing else. So this read saw `undefined`,
// fell back to 8080, and `npm run dev` proxied every API call to a
// port with nothing on it: the app loaded and reported the agent
// offline, which looks like a broken agent rather than a broken
// proxy.
//
// `loadEnv` with an empty prefix is vite's own reader for the same
// files, so the dev server and the BFF now get the port from one
// place. An explicit PORT in the environment still wins.
const env = loadEnv(process.env.NODE_ENV || "development", process.cwd(), "");
const bffPort = process.env.PORT || env.PORT || 8080;
const proxyTarget = `http://127.0.0.1:${bffPort}`;

export default defineConfig({
  plugins: [patternflyLayer(), react(), tailwindcss(), cssLayerOrder(), precompressAssets()],
  // Relative, because the bundle is served from /dist/frontend (and from
  // ${BASE_PATH}/dist/frontend when that is set), not from the origin root.
  // With the default base of '/', the font URLs inside the stylesheet came
  // out as `/assets/…` and 404'd — the app has been falling back to system
  // fonts. Relative URLs resolve against the stylesheet, so they are correct
  // under any prefix.
  base: "./",
  build: {
    // Deliberately NOT `build.lib`. Library mode emits one UMD file with no
    // code splitting and no content hashes, which meant the whole app — admin
    // screens, eval tooling, the lot — was a single render-blocking download
    // on every first paint. A plain multi-entry build gives per-route chunks
    // (see the React.lazy calls in App.tsx) and hashed, immutably-cacheable
    // filenames. The server resolves names through `.vite/manifest.json`.
    outDir: path.resolve(__dirname, "dist/frontend"),
    emptyOutDir: true,
    manifest: true,
    sourcemap: true,
    // Left at the default (true) on purpose: with it off Vite emits a
    // `style.css` that is attributed to no chunk, so the manifest entry has
    // no `css` array and the server has nothing to link.
    cssCodeSplit: true,
    rollupOptions: {
      input: path.resolve(__dirname, "src/frontend/main.tsx"),
      output: {
        format: "es",
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
        // Only React is pinned to its own chunk: it is the one dependency
        // every route needs, so isolating it keeps it cached across app
        // deploys. Everything else is left to Rollup, which places a module
        // in a shared chunk only when more than one route actually imports
        // it — a hand-written catch-all `return "vendor"` instead drags
        // route-only libraries (recharts, the MCP client) into the eager
        // first load.
        manualChunks(id) {
          if (/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler)\//.test(id)) {
            return "vendor-react";
          }
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src/frontend"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: proxyTarget,
        changeOrigin: true,
      },
      "/auth": {
        target: proxyTarget,
        changeOrigin: true,
      },
      "/login": {
        target: proxyTarget,
        changeOrigin: true,
      },
      // Both are served by the BFF in production. Without these the
      // dev server answers them with the SPA's HTML, so the worker
      // never registers and the manifest never parses — a feature
      // that works only in the built image is a feature nobody
      // tests until it is too late to notice.
      "/sw.js": {
        target: proxyTarget,
        changeOrigin: true,
      },
      "/manifest.webmanifest": {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
  define: {
    "process.env": {
      ENVIRONMENT: process.env.ENVIRONMENT,
    }, // Polyfill process.env with an empty object
  },
});
