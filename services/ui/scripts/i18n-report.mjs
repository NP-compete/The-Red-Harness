#!/usr/bin/env node
/**
 * Every English sentence written into a component instead of the
 * catalogue.
 *
 * Strings live in one file so they can be found, reviewed and
 * changed in one place. That only holds if new ones keep going
 * there, and the way it stops holding is undramatic: somebody
 * types a label directly into a component, nothing breaks, and
 * the catalogue is quietly no longer the whole of the product's
 * wording.
 *
 * The defence used to be a test naming the files somebody had
 * already thought about — which works until somebody adds a
 * file. So this reads every component instead.
 *
 * Parsed, not matched. A regular expression over source cannot
 * tell `'Save'` in a label from `'Save'` inside a `t()` call it
 * is already the argument to, and the second is correct code. A
 * sweep that fires on correct code is a sweep somebody deletes.
 *
 * Two places a string becomes visible, and the second is the one
 * regular-expression sweeps miss:
 *
 * - **In the markup.** Text between tags, and the attributes a
 *   screen reader reads: `aria-label`, `title`, `placeholder`,
 *   `alt`.
 * - **In a configuration object.** `{ label: 'Save' }` in a
 *   table of columns or a list of tabs renders exactly like
 *   markup and looks nothing like it.
 *
 * Run it for the list: `node scripts/i18n-report.mjs`.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import ts from 'typescript';

const HERE = dirname(fileURLToPath(import.meta.url));
export const ROOT = join(HERE, '..', 'src', 'frontend');

// Attributes a person reads or hears. `className`, `id`, `key`
// and the rest are machinery, and flagging them would bury the
// real findings.
const SPOKEN_ATTRIBUTES = new Set([
  'alt',
  'aria-label',
  'aria-placeholder',
  'aria-roledescription',
  'aria-valuetext',
  'placeholder',
  'title',
]);

// Property names that end up on screen. Conservative on
// purpose: `name` and `value` are far more often an identifier
// than a label, and a sweep with a false positive in it is one
// people learn to ignore.
const SPOKEN_PROPERTIES = new Set([
  'ariaLabel',
  // Added when the segment matcher went in: a greeting is the
  // most read string in the product and was not on this list.
  'greeting',
  'confirmLabel',
  'description',
  'emptyMessage',
  'heading',
  'helpText',
  'label',
  'placeholder',
  'subtitle',
  'tooltip',
]);

/**
 * Whether a property name is one a person reads the value of.
 *
 * Matched on the last underscore-separated segment, not on the
 * whole name. The exact-match version read `subtitle` and missed
 * `input_placeholder`, `welcome_heading` and
 * `quick_prompts_heading` *in the same object* — so the report
 * said one untranslated string where there were nine, and the
 * number looked like progress.
 */
export function isSpokenProperty(name) {
  if (!name) return false;
  if (SPOKEN_PROPERTIES.has(name)) return true;
  const last = String(name).split('_').pop();
  return SPOKEN_PROPERTIES.has(last);
}

/**
 * Whether this string is deliberately in English, and said so.
 *
 * A marker rather than a list of filenames here: the reason
 * lives next to the code it excuses, where somebody deleting the
 * code deletes the exemption with it.
 *
 *     // i18n-exempt: mirrors the server's own defaults
 *
 * The walk stops below the file node on purpose. Reading the
 * file's own leading comments made one marker at the top excuse
 * every string below it — an exemption that grows silently is
 * worse than no exemption at all.
 */
function isExempt(node, source) {
  let current = node;
  while (current && !ts.isSourceFile(current)) {
    const comments = ts.getLeadingCommentRanges(source, current.getFullStart()) || [];
    for (const range of comments) {
      if (source.slice(range.pos, range.end).includes('i18n-exempt')) return true;
    }
    current = current.parent;
  }
  return false;
}

/** Whether a literal reads as something written for a person. */
export function looksLikeProse(text) {
  const trimmed = (text || '').trim();
  if (trimmed.length < 3) return false;
  // An entity is layout, not wording. `&nbsp;&nbsp;` between two
  // figures is a gap somebody could not get from CSS, and asking
  // a translator for it wastes the one attention this list has.
  if (/^(&[a-z]+;|&#\d+;|\s)+$/i.test(trimmed)) return false;
  // A path, a URL, a MIME type, a CSS class, an identifier.
  if (/^[\w.-]+$/.test(trimmed)) return false;
  if (/^(https?:|\/|\.{1,2}\/|#|data:|mailto:)/.test(trimmed)) return false;
  // A run of class names: several lowercase tokens, no sentence.
  if (/^[a-z0-9:_\-[\]/. ]+$/.test(trimmed) && !/[A-Z]/.test(trimmed)) {
    return /\s/.test(trimmed) ? false : false;
  }
  return /[A-Za-z]{3}/.test(trimmed);
}

function isTranslatorCall(node) {
  if (!ts.isCallExpression(node)) return false;
  const callee = node.expression;
  if (ts.isIdentifier(callee)) return callee.text === 't' || callee.text === 'tt';
  if (ts.isPropertyAccessExpression(callee)) return callee.name.text === 't';
  return false;
}

function textOf(node) {
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
    return node.text;
  }
  return null;
}

/**
 * Every untranslated string in one file's source.
 *
 * Takes source rather than a path so a planted example can be
 * checked without writing a file.
 */
export function untranslatedIn(source, fileName = 'x.tsx') {
  const tree = ts.createSourceFile(
    fileName,
    source,
    ts.ScriptTarget.Latest,
    true,
    fileName.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const found = [];

  const note = (node, text, where) => {
    const { line } = tree.getLineAndCharacterOfPosition(node.getStart(tree));
    found.push({ line: line + 1, text: text.trim(), where });
  };

  const walk = (node) => {
    // Anything inside a translator call is already going through
    // the catalogue — including its interpolation values, which
    // are the sentence's own parts.
    if (isTranslatorCall(node)) return;

    if (ts.isJsxText(node)) {
      // JSX collapses whitespace, so a text node that is only
      // layout is not a string anybody reads.
      if (looksLikeProse(node.text) && !isExempt(node, source)) {
        note(node, node.text, 'markup');
      }
    } else if (ts.isJsxAttribute(node)) {
      const name = node.name.getText(tree);
      if (SPOKEN_ATTRIBUTES.has(name) && node.initializer) {
        const literal =
          textOf(node.initializer) ??
          (ts.isJsxExpression(node.initializer) && node.initializer.expression
            ? textOf(node.initializer.expression)
            : null);
        if (literal !== null && looksLikeProse(literal) && !isExempt(node, source)) {
          note(node, literal, name);
        }
      }
    } else if (ts.isPropertyAssignment(node)) {
      const name = ts.isIdentifier(node.name)
        ? node.name.text
        : ts.isStringLiteral(node.name)
          ? node.name.text
          : '';
      if (isSpokenProperty(name)) {
        const literal = textOf(node.initializer);
        if (literal !== null && looksLikeProse(literal) && !isExempt(node, source)) {
          note(node, literal, name);
        }
      }
    }

    ts.forEachChild(node, walk);
  };

  ts.forEachChild(tree, walk);
  return found;
}

function isComponentSource(path) {
  if (!/\.tsx?$/.test(path)) return false;
  // Tests write English on purpose: an expectation naming the
  // text on screen is the test doing its job.
  if (/\.test\.tsx?$/.test(path)) return false;
  if (path.includes(`${'__tests__'}`)) return false;
  // The catalogue itself, and the setup that loads it.
  if (path.includes(join('i18n', 'locales'))) return false;
  return true;
}

export function componentFiles(root = ROOT) {
  const out = [];
  const walk = (dir) => {
    for (const entry of readdirSync(dir)) {
      const path = join(dir, entry);
      if (statSync(path).isDirectory()) {
        walk(path);
      } else if (isComponentSource(path)) {
        out.push(path);
      }
    }
  };
  walk(root);
  return out.sort();
}

/** Every untranslated string across the interface. */
export function sweep(root = ROOT) {
  const findings = [];
  for (const path of componentFiles(root)) {
    for (const one of untranslatedIn(readFileSync(path, 'utf-8'), path)) {
      findings.push({ ...one, file: relative(root, path) });
    }
  }
  return findings;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split('/').pop())) {
  const findings = sweep();
  for (const f of findings) {
    console.log(`${f.file}:${f.line}  [${f.where}]  ${JSON.stringify(f.text)}`);
  }
  console.log(`\n${findings.length} untranslated strings in ${componentFiles().length} files`);
  // A report nobody fails is a report nobody reads. It printed
  // its findings and exited 0, so it could be wired into CI and
  // still never stop anything — the exit code that cannot fail.
  // The count is zero today, so this starts as a ratchet rather
  // than a backlog: the next string typed into a component is
  // the one that has to go in the catalogue.
  process.exitCode = findings.length > 0 ? 1 : 0;
}
