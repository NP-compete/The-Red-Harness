/**
 * What the search weighed, for somebody asking why it missed.
 *
 * "Your document was not used" covers three different problems
 * with three different fixes: it was out of scope, it shared no
 * words with the question, or it scored just under the
 * threshold somebody set. Only the last leaves a row here, and
 * seeing that row is the difference between changing a setting
 * and giving up.
 */

export interface SearchedRecord {
  id: string;
  title: string;
  scope: string;
  score: number;
  used: boolean;
}

export interface SearchedRow {
  id: string;
  title: string;
  scope: string;
  match: string;
  used: boolean;
}

export interface SearchedView {
  usedCount: number;
  missedCount: number;
  rows: SearchedRow[];
}

function asMatch(score: unknown): string {
  // An em dash rather than 0%. A score nobody recorded is not
  // a document that matched nothing.
  if (typeof score !== 'number' || Number.isNaN(score)) return '—';
  return `${Math.round(score * 100)}%`;
}

export function describeSearched(
  record: SearchedRecord[] | undefined,
): SearchedView | null {
  if (!Array.isArray(record) || record.length === 0) return null;

  const ranked = [...record].sort((a, b) => {
    // Near misses first: the documents that were used are
    // already named in the citations above, and repeating
    // them first buries the only new thing here.
    if (a.used !== b.used) return a.used ? 1 : -1;
    return (b.score ?? 0) - (a.score ?? 0);
  });

  return {
    usedCount: record.filter((row) => row.used).length,
    missedCount: record.filter((row) => !row.used).length,
    rows: ranked.map((row) => ({
      id: row.id,
      title: row.title || row.id,
      scope: row.scope,
      match: asMatch(row.score),
      used: row.used,
    })),
  };
}
