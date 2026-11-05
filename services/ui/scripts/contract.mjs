#!/usr/bin/env node
/**
 * Generate the agent's payload types from its OpenAPI baseline, and
 * fail when the committed output no longer matches (E10-T13, T15).
 *
 * The contract is currently written twice — the agent emits
 * `tests/contracts/openapi-baseline.json`, the UI hand-writes types
 * describing the same payloads, and nothing compares them. That gap
 * is how an interrupt payload shipped as a JSON string against a type
 * that said otherwise, and the symptom was a conversation that
 * stopped with nothing on screen to say why.
 *
 * `--check` regenerates to a temporary file and compares. A mismatch
 * means somebody changed a route and did not regenerate, so the error
 * says exactly that rather than printing 11k lines of diff.
 *
 * Both components live in one repository now, so the baseline is an
 * in-tree path (`tests/fixtures/`) rather than a sibling checkout.
 * It is still checked for existence so a missing file fails with a
 * sentence instead of a stack.
 */
import { execFileSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const SOURCE = path.resolve(root, '../../tests/fixtures/openapi-baseline.json');
const TARGET = path.join(root, 'src/frontend/types/generated/agent-api.d.ts');

const check = process.argv.includes('--check');

if (!fs.existsSync(SOURCE)) {
  console.error(
    `no OpenAPI baseline at ${SOURCE}\n` +
      'Generate it with `make openapi-baseline`.',
  );
  process.exit(1);
}

function generate(out) {
  execFileSync('npx', ['openapi-typescript', SOURCE, '-o', out], {
    cwd: root,
    stdio: ['ignore', 'ignore', 'inherit'],
  });
}

if (!check) {
  fs.mkdirSync(path.dirname(TARGET), { recursive: true });
  generate(TARGET);
  console.log(`wrote ${path.relative(root, TARGET)} from ${path.relative(root, SOURCE)}`);
  process.exit(0);
}

const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'contract-')), 'agent-api.d.ts');
generate(tmp);

if (!fs.existsSync(TARGET)) {
  console.error(`${path.relative(root, TARGET)} is missing. Run \`npm run contract\`.`);
  process.exit(1);
}

const fresh = fs.readFileSync(tmp, 'utf8');
const committed = fs.readFileSync(TARGET, 'utf8');

if (fresh === committed) {
  console.log('the generated contract matches the agent’s OpenAPI baseline');
  process.exit(0);
}

// Name the routes that moved. A reviewer can act on "these three
// endpoints changed"; they cannot act on a character count.
const routes = (text) => new Set((text.match(/^ {4}"\/[^"]*"/gm) || []).map((s) => s.trim()));
const before = routes(committed);
const after = routes(fresh);
const added = [...after].filter((r) => !before.has(r));
const removed = [...before].filter((r) => !after.has(r));

console.error('the committed contract is stale.');
if (added.length) console.error(`  added:   ${added.join(', ')}`);
if (removed.length) console.error(`  removed: ${removed.join(', ')}`);
if (!added.length && !removed.length) {
  console.error('  the paths are the same, so a payload shape changed.');
}
console.error('Run `npm run contract` and commit the result.');
process.exit(1);
