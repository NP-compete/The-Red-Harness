#!/usr/bin/env node
/**
 * Move a string out of a component and into the catalogue.
 *
 * The sweep next door says where they are. Doing anything about
 * them by hand means matching the exact whitespace a formatter
 * chose, in a hundred places, and a near-miss there edits the
 * wrong line rather than failing — so this splices by the
 * position the parser reports instead.
 *
 * Takes a plan: `{ "file.tsx": { "text on screen": "key.name" } }`.
 * Writes the catalogue entry, rewrites the component, and says
 * what it could not find rather than guessing.
 *
 *   node scripts/i18n-move.mjs plan.json
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import ts from 'typescript';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', 'src', 'frontend');
const CATALOGUE = join(ROOT, 'i18n', 'locales', 'en.json');

/** Every place in one file where a literal could be swapped. */
function sites(source, fileName) {
  const tree = ts.createSourceFile(
    fileName,
    source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
  const found = [];
  const walk = (node) => {
    if (ts.isJsxText(node)) {
      found.push({ kind: 'text', text: node.text.trim(), start: node.getStart(tree), end: node.end });
    } else if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      // Braces only where the grammar needs them. A JSX
      // attribute takes `{t('k')}`; everywhere else — an
      // object property, an argument — `{...}` is a block and
      // the file stops parsing.
      const inJsxAttribute = node.parent && ts.isJsxAttribute(node.parent);
      found.push({
        kind: inJsxAttribute ? 'attribute' : 'expression',
        text: node.text,
        start: node.getStart(tree),
        end: node.end,
      });
    }
    ts.forEachChild(node, walk);
  };
  ts.forEachChild(tree, walk);
  return found;
}

/**
 * One file's source with each planned string replaced by a call.
 *
 * Pure, so the brace rule can be checked without a tree on disk.
 * Returns the strings it could not find rather than guessing at
 * a near match.
 */
export function rewrite(source, strings, fileName = 'x.tsx') {
  const absent = [];
  const edits = [];
  for (const [text, key] of Object.entries(strings)) {
    const candidates = sites(source, fileName).filter((s) => s.text === text);
    if (candidates.length === 0) {
      absent.push(text);
      continue;
    }
    for (const site of candidates) edits.push({ ...site, key });
  }
  // Last first, so an earlier splice does not move a later one.
  edits.sort((a, b) => b.start - a.start);
  for (const edit of edits) {
    const call = `t('${edit.key}')`;
    const replacement = edit.kind === 'expression' ? call : `{${call}}`;
    source = source.slice(0, edit.start) + replacement + source.slice(edit.end);
  }
  return { source, absent, moved: edits.length };
}

// Importing this module must not run it: the tests read
// `rewrite` above, and a plan file is only there when a
// person asked for one on the command line.
if (process.argv[2]) {
  const plan = JSON.parse(readFileSync(process.argv[2], 'utf-8'));
  const catalogue = JSON.parse(readFileSync(CATALOGUE, 'utf-8'));
  const missed = [];
  let moved = 0;

  for (const [file, strings] of Object.entries(plan)) {
    const path = join(ROOT, file);
    const done = rewrite(readFileSync(path, 'utf-8'), strings, path);
    writeFileSync(path, done.source);
    moved += done.moved;
    for (const text of done.absent) missed.push(`${file}: ${JSON.stringify(text)}`);
  }

  // The catalogue last, so a run that found nothing leaves no
  // orphan entries behind.
  for (const strings of Object.values(plan)) {
    for (const [text, key] of Object.entries(strings)) {
      const [namespace, ...rest] = key.split('.');
      const leaf = rest.join('.');
      catalogue[namespace] = catalogue[namespace] ?? {};
      if (catalogue[namespace][leaf] !== undefined && catalogue[namespace][leaf] !== text) {
        // Overwriting a key somebody else already uses changes
        // their wording silently.
        missed.push(`CLASH ${key}: already ${JSON.stringify(catalogue[namespace][leaf])}`);
        continue;
      }
      catalogue[namespace][leaf] = text;
    }
  }
  writeFileSync(CATALOGUE, `${JSON.stringify(catalogue, null, 2)}\n`);

  console.log(`moved ${moved}`);
  if (missed.length) {
    console.log('could not place:');
    for (const one of missed) console.log('  ' + one);
  }
}
