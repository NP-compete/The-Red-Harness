export type ResultShape =
  | 'table'
  | 'fields'
  | 'list'
  | 'text'
  | 'code'
  | 'json'
  | 'empty';

export interface ResultState {
  shape: ResultShape;
  rows: number;
  columns: string[];
  language: string;
  needsPaging: boolean;
  needsCollapsing: boolean;
  tool: string;
  trusted: boolean;
}

/**
 * What the result is, rather than a sentence about it.
 *
 * A table counts rows and columns independently and a catalogue key
 * carries only one count, so the words are assembled where there is
 * a translator to assemble them.
 */
export type ResultSummary =
  | { kind: 'empty'; tool: string }
  | { kind: 'table'; rows: number; columns: number }
  | { kind: 'json'; rows: number }
  | { kind: 'list'; rows: number }
  | { kind: 'code'; language: string }
  | { kind: 'text' };

export interface PresentedResult {
  summary: ResultSummary;
  render: ResultShape;
  language: string;
  paged: boolean;
  collapsed: boolean;
  fenced: boolean;
  actions: string[];
}

const DOWNLOADABLE = new Set<ResultShape>(['table', 'json', 'list', 'code', 'text', 'fields']);

export function presentResult(result: ResultState): PresentedResult {
  const empty = result.shape === 'empty';

  return {
    summary: summarise(result),
    render: result.shape,
    language: result.language,
    paged: result.needsPaging,
    collapsed: result.needsCollapsing,
    // Tool output is someone else's text: it is shown as data, never as
    // something the model or the reader should act on.
    fenced: !result.trusted,
    actions: empty ? [] : ['copy', ...(DOWNLOADABLE.has(result.shape) ? ['download'] : [])],
  };
}

function summarise(result: ResultState): ResultSummary {
  if (result.shape === 'empty') return { kind: 'empty', tool: result.tool };

  if (result.shape === 'table') {
    return { kind: 'table', rows: result.rows, columns: result.columns.length };
  }

  // Raw data is described as raw data rather than dressed up as a table.
  if (result.shape === 'json') return { kind: 'json', rows: result.rows };

  if (result.shape === 'list') return { kind: 'list', rows: result.rows };

  if (result.shape === 'code') return { kind: 'code', language: result.language };

  return { kind: 'text' };
}
