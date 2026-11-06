#!/usr/bin/env node
/**
 * Give a component the translator it has started calling.
 *
 * The companion to the move script: that one replaces a string
 * with `t('key')`, which only compiles where a `t` is in scope.
 * Adding the hook by hand to twenty files is twenty chances to
 * put it inside a callback, where it is a hook-order bug rather
 * than a compile error.
 *
 * So this finds the function that actually needs it. Two rules,
 * both learned the hard way:
 *
 * - **Outermost, not innermost.** A `map` callback inside a
 *   component mentions `t` too, and a hook called there runs a
 *   different number of times on different renders.
 * - **A class gets nothing.** Hooks do not run in one, and
 *   silently adding a call that cannot work is worse than the
 *   compile error it was meant to fix. Those are reported for
 *   somebody to handle.
 *
 *   node scripts/i18n-hook.mjs Component.tsx OtherComponent.tsx
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import ts from 'typescript';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', 'src', 'frontend');

/** Where the hook belongs in this source, and what is out of reach. */
export function placements(source, fileName = 'x.tsx') {
  const tree = ts.createSourceFile(fileName, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const wants = [];
  const classes = [];

  const walk = (node) => {
    if (ts.isClassDeclaration(node) && /[^\w.']\bt\('/.test(node.getText(tree))) {
      classes.push(node.name ? node.name.text : 'a class');
    }
    const isFunction =
      ts.isFunctionDeclaration(node) || ts.isArrowFunction(node) || ts.isFunctionExpression(node);
    if (isFunction && node.body && ts.isBlock(node.body)) {
      const body = node.body.getText(tree);
      const declaresIt = /const\s*\{\s*t\s*[,}]/.test(body);
      const callsIt = /[^\w.']\bt\('/.test(body);
      if (callsIt && !declaresIt) {
        wants.push({ at: node.body.getStart(tree) + 1, from: node.body.getStart(tree), to: node.body.end });
      }
    }
    ts.forEachChild(node, walk);
  };
  ts.forEachChild(tree, walk);

  // A callback inside a component is not a place for a hook.
  const outermost = wants.filter(
    (one) => !wants.some((other) => other !== one && other.from < one.from && one.to <= other.to),
  );
  // Nothing inside a class: `placements` reports it instead.
  return { outermost, classes };
}

export function withHook(source, fileName = 'x.tsx') {
  const { outermost, classes } = placements(source, fileName);
  if (outermost.length === 0) return { source, added: 0, classes };

  let out = source;
  for (const one of [...outermost].sort((a, b) => b.at - a.at)) {
    out = `${out.slice(0, one.at)}\n  const { t } = useTranslation();${out.slice(one.at)}`;
  }
  if (!/from ['"]react-i18next['"]/.test(out)) {
    // After the last import *declaration*, which the parser
    // knows and a line scan does not: the last line starting
    // with `import` is the opening line of a multi-line block,
    // and inserting there splices the new import between the
    // brace and its names.
    const parsed = ts.createSourceFile(fileName, out, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    const imports = parsed.statements.filter((one) => ts.isImportDeclaration(one));
    const after = imports.length ? imports[imports.length - 1].end : 0;
    out = `${out.slice(0, after)}\nimport { useTranslation } from 'react-i18next';${out.slice(after)}`;
  }
  return { source: out, added: outermost.length, classes };
}

if (process.argv.length > 2) {
  for (const relative of process.argv.slice(2)) {
    const path = join(ROOT, relative);
    const done = withHook(readFileSync(path, 'utf-8'), path);
    writeFileSync(path, done.source);
    const note = done.classes.length ? `  (no hook possible in ${done.classes.join(', ')})` : '';
    console.log(`${relative}: ${done.added}${note}`);
  }
}
