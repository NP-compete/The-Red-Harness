#!/usr/bin/env node
/**
 * Report translation keys a component asks for that no locale defines.
 *
 * `i18n-report.mjs` checks one direction — an English sentence typed
 * into a component instead of the catalogue. This checks the other,
 * which nothing did: a component calling `t('a.b')` for a key the
 * catalogue does not define. That failure is quiet, because i18next
 * renders the key itself, so the screen shows `settings.saveLabel`
 * where a sentence should be and no test notices.
 *
 * `en.json` is the reference. This tree ships one locale, so it is
 * also the only one.
 *
 * Exits non-zero when a key is missing, which makes it usable in CI,
 * but it is a script rather than a test for the same reason
 * `i18n-report.mjs` is: the repo has literal keys it cannot resolve
 * statically, and a check that has to be switched off is not a check.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const SRC = fileURLToPath(new URL('../src/frontend', import.meta.url));
const EN = fileURLToPath(new URL('../src/frontend/i18n/locales/en.json', import.meta.url));

// `t('a.b')` and `t("a.b")`. A key with no dot is not one of ours.
const LITERAL = /\bt\(\s*['"]([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)['"]/g;

// `` t(`a.b.${x}`) `` — the prefix is checkable even when the leaf is
// not. Worth doing: 14 of the 32 keys in one restored block were built
// this way, so a literal-only sweep reported the block as fine while
// half of it was absent.
const TEMPLATE = /\bt\(\s*`([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\.\$\{/g;

// Tests and fixtures are skipped. They call `t('x.y')` against a stub
// to prove the stub works, and a key that was never meant to resolve
// reported as missing would be the noise that gets the whole check
// ignored.
const NOT_SHIPPED = /(\.test\.(ts|tsx)$|__tests__|test-utils)/;

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (NOT_SHIPPED.test(path)) continue;
    if (statSync(path).isDirectory()) walk(path, out);
    else if (/\.(ts|tsx)$/.test(name)) out.push(path);
  }
  return out;
}

// i18next resolves `t('counts.rows', {count})` against `rows_one` and
// `rows_other`, never against a bare `rows`. Without this the check
// reported 26 perfectly good plural keys as missing on its first run
// here — and a check that cries wolf is one people switch off.
const PLURALS = ['_zero', '_one', '_two', '_few', '_many', '_other'];

function has(tree, path) {
  let node = tree;
  const parts = path.split('.');
  for (const [i, part] of parts.entries()) {
    if (typeof node !== 'object' || node === null) return false;
    if (part in node) {
      node = node[part];
      continue;
    }
    // Only the leaf can be a plural family, and English needs both
    // halves of it: with `_other` missing, every count but one
    // renders the key instead of a sentence — which is the same
    // silent failure as a missing key, in fewer places.
    if (i === parts.length - 1 && PLURALS.some((s) => part + s in node)) {
      return `${part}_one` in node && `${part}_other` in node;
    }
    return false;
  }
  return true;
}

const en = JSON.parse(readFileSync(EN, 'utf8'));
const missing = new Map();

for (const file of walk(SRC)) {
  const source = readFileSync(file, 'utf8');
  const found = [
    ...[...source.matchAll(LITERAL)].map((m) => [m[1], false]),
    // A prefix is present if it resolves to an object with anything in
    // it; an empty one means the block was emptied rather than filled.
    ...[...source.matchAll(TEMPLATE)].map((m) => [m[1], true]),
  ];
  for (const [key, isPrefix] of found) {
    const ok = isPrefix
      ? has(en, key) && Object.keys(en[key.split('.')[0]] ?? {}).length > 0
      : has(en, key);
    if (ok) continue;
    const where = relative(SRC, file);
    if (!missing.has(key)) missing.set(key, { where, isPrefix });
  }
}

if (missing.size === 0) {
  console.log('every key a component asks for is defined in en.json');
  process.exit(0);
}

console.log(`${missing.size} key(s) called but not defined:\n`);
for (const [key, { where, isPrefix }] of [...missing].sort()) {
  console.log(`  ${key}${isPrefix ? '.*' : ''}  —  ${where}`);
}
process.exit(1);
