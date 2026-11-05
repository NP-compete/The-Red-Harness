#!/usr/bin/env node
/**
 * Build the shell worker to a fixed path.
 *
 * Separate from the application bundle because the registration
 * path cannot carry a content hash: the browser looks for exactly
 * the URL it was registered with, and a hashed filename would make
 * every release register a different worker while the old one kept
 * serving.
 *
 * Scope matters too. A worker served from `/dist/frontend/sw.js`
 * controls only that directory; it has to sit at the root to see
 * navigations.
 */
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

await build({
  entryPoints: [resolve(root, 'src/frontend/sw.ts')],
  outfile: resolve(root, 'dist/frontend/sw.js'),
  bundle: true,
  format: 'iife',
  target: 'es2020',
  minify: true,
  sourcemap: true,
  logLevel: 'info',
});
