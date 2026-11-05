import { describe, expect, it } from 'vitest';

import { presentResult } from '@/lib/tool-result-view';

import en from '../i18n/locales/en.json';

/**
 * `summary` describes the result rather than wording it: a table
 * counts rows and columns independently, and a catalogue key can
 * carry only one count. Composing here keeps each assertion about
 * the sentence a person reads.
 */
function plural(section: string, name: string, count: number): string {
  const table = (en as Record<string, Record<string, string>>)[section] ?? {};
  const form = table[`${name}_${count === 1 ? 'one' : 'other'}`] ?? table[name];
  if (form === undefined) throw new Error(`no English string for '${section}.${name}'`);
  return form.replace('{{count}}', String(count));
}

function said(summary: ReturnType<typeof presentResult>['summary']): string {
  switch (summary.kind) {
    case 'empty':
      return en.toolResult.empty.replace('{{tool}}', summary.tool);
    case 'table':
      return `${plural('counts', 'rows', summary.rows)}, ${plural('toolResult', 'columns', summary.columns)}`;
    case 'json':
      return plural('toolResult', 'mixed', summary.rows);
    case 'list':
      return plural('toolResult', 'items', summary.rows);
    case 'code':
      return en.toolResult.snippet.replace('{{language}}', summary.language || en.toolResult.code);
    default:
      return en.toolResult.text;
  }
}

const table = {
  shape: 'table' as const,
  rows: 3,
  columns: ['cost', 'name'],
  language: '',
  needsPaging: false,
  needsCollapsing: false,
  tool: 'search',
  trusted: false,
};

describe('presentResult', () => {
  it('describes a table by its size', () => {
    expect(said(presentResult(table).summary)).toBe('3 rows, 2 columns');
  });

  it('uses the singular for one row', () => {
    expect(said(presentResult({ ...table, rows: 1 }).summary)).toBe('1 row, 2 columns');
  });

  it('renders a table as a table', () => {
    expect(presentResult(table).render).toBe('table');
  });

  it('pages a large table rather than dumping it', () => {
    expect(presentResult({ ...table, rows: 500, needsPaging: true }).paged).toBe(true);
  });

  it('does not page a small table', () => {
    expect(presentResult(table).paged).toBe(false);
  });

  it('renders code with its language', () => {
    const code = { ...table, shape: 'code' as const, language: 'python', rows: 0, columns: [] };
    expect(presentResult(code).render).toBe('code');
    expect(presentResult(code).language).toBe('python');
  });

  it('collapses a very long result by default', () => {
    const long = { ...table, shape: 'text' as const, needsCollapsing: true, rows: 0, columns: [] };
    expect(presentResult(long).collapsed).toBe(true);
  });

  it('leaves a short result open', () => {
    const short = { ...table, shape: 'text' as const, rows: 0, columns: [] };
    expect(presentResult(short).collapsed).toBe(false);
  });

  it('says plainly when a tool returned nothing', () => {
    const empty = { ...table, shape: 'empty' as const, rows: 0, columns: [] };
    expect(said(presentResult(empty).summary)).toBe('search returned nothing');
  });

  it('marks untrusted output so it is not read as instructions', () => {
    expect(presentResult(table).fenced).toBe(true);
  });

  it('does not fence output from a trusted source', () => {
    expect(presentResult({ ...table, trusted: true }).fenced).toBe(false);
  });

  it('falls back to raw data for an awkward shape', () => {
    const messy = { ...table, shape: 'json' as const, columns: [] };
    expect(presentResult(messy).render).toBe('json');
  });

  it('describes raw data without pretending it is a table', () => {
    const messy = { ...table, shape: 'json' as const, columns: [], rows: 2 };
    expect(said(presentResult(messy).summary)).toBe('2 items of mixed shape');
  });

  it('offers to copy any result', () => {
    expect(presentResult(table).actions).toContain('copy');
  });

  it('offers to download a table', () => {
    expect(presentResult(table).actions).toContain('download');
  });

  it('does not offer to download nothing', () => {
    const empty = { ...table, shape: 'empty' as const, rows: 0, columns: [] };
    expect(presentResult(empty).actions).toEqual([]);
  });
});
