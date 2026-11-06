/**
 * The documents an answer came from, as the reader sees them.
 *
 * Only what the answer borrowed from. A strip listing everything
 * retrieval touched looks thorough and teaches a reader that
 * citations are not worth opening.
 */

export interface CitationRecord {
  document_id: string;
  title: string;
  scope: string;
}

export type Origin = 'session' | 'user' | 'agent' | 'unknown';

export interface CitationView {
  documentId: string;
  title: string;
  origin: Origin;
}

const ORIGINS: readonly string[] = ['session', 'user', 'agent'];

export function describeCitations(
  cited: CitationRecord[] | undefined,
): CitationView[] | null {
  if (!Array.isArray(cited) || cited.length === 0) return null;

  const found = cited
    .filter((entry) => entry && typeof entry.document_id === 'string')
    .map((entry) => ({
      documentId: entry.document_id,
      title: entry.title || entry.document_id,
      // Unknown rather than shown verbatim: a word from the
      // agent would appear untranslated in every locale.
      origin: (ORIGINS.includes(entry.scope) ? entry.scope : 'unknown') as Origin,
    }));

  return found.length > 0 ? found : null;
}
