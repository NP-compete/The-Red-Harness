#!/usr/bin/env node
/**
 * The packages the BFF server actually imports, as a manifest.
 *
 * The runtime image shipped all 615 installed packages so that a
 * Fastify server could import a dozen; the rest is frontend that
 * vite has already bundled into `dist/frontend`.
 *
 * Derived rather than hand-maintained: a second dependency list
 * falls behind the first the next time somebody adds an import.
 * Versions come from the real package.json. Anything imported but
 * not in `dependencies` is reported and left out.
 *
 *   node scripts/server-deps.mjs > package.server.json
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const SERVER = join(ROOT, "src", "server");

/** Every .ts file under src/server, excluding tests. */
function sources(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      if (entry === "__tests__" || entry === "node_modules") continue;
      out.push(...sources(path));
    } else if (entry.endsWith(".ts") && !entry.endsWith(".test.ts")) {
      out.push(path);
    }
  }
  return out;
}

// `from "x"`, `import "x"`, `require("x")` and `import("x")`.
const SPECIFIER = /(?:from|import|require)\s*\(?\s*["']([^"']+)["']/g;

/** `@scope/name/deep` → `@scope/name`; `name/deep` → `name`. */
function packageOf(specifier) {
  const parts = specifier.split("/");
  return specifier.startsWith("@") ? parts.slice(0, 2).join("/") : parts[0];
}

const manifest = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
const declared = manifest.dependencies ?? {};

const used = new Set();
const undeclared = new Set();
for (const file of sources(SERVER)) {
  const text = readFileSync(file, "utf8");
  for (const [, specifier] of text.matchAll(SPECIFIER)) {
    // Relative imports and node builtins need nothing installed.
    if (specifier.startsWith(".") || specifier.startsWith("node:")) continue;
    // A bare specifier has no spaces; without this the scanner
    // reports fragments of prose from message strings.
    if (/\s/.test(specifier)) continue;
    const name = packageOf(specifier);
    if (name in declared) used.add(name);
    else undeclared.add(name);
  }
}

// vitest lands here because tests import it and they are excluded
// from the image; anything else is a forgotten declaration.
if (undeclared.size) {
  process.stderr.write(
    `server-deps: imported but not in dependencies — ${[...undeclared].sort().join(", ")}\n`
  );
}

const out = {
  name: `${manifest.name}-server`,
  version: manifest.version,
  private: true,
  type: manifest.type,
  dependencies: Object.fromEntries(
    [...used].sort().map((name) => [name, declared[name]])
  ),
  // The overrides come too. This manifest is installed in the image
  // with a plain `npm install` — no lockfile, nothing to pin a
  // transitive dependency — so without them the image resolved
  // `@opentelemetry/propagator-jaeger@2.7.1` while the repository's
  // lock said 2.12.0, and the image scan reported a HIGH the
  // interface had already fixed. An override that only applies to
  // the tree nobody ships is not an override.
  overrides: manifest.overrides ?? {},
};

const target = join(ROOT, "package.server.json");
writeFileSync(target, JSON.stringify(out, null, 2) + "\n");
process.stderr.write(
  `server-deps: ${used.size} of ${Object.keys(declared).length} dependencies are reachable from the server\n`
);
