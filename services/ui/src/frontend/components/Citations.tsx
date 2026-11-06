import { useTranslation } from 'react-i18next';
import { FileText } from 'lucide-react';

import {
  describeCitations,
  type CitationRecord,
  type Origin,
} from '../lib/citation-view';

const ORIGIN_KEY: Record<Origin, string> = {
  agent: 'citations.fromAgent',
  user: 'citations.fromYou',
  session: 'citations.fromConversation',
  unknown: 'citations.fromUnknown',
};

/**
 * The documents an answer came from.
 *
 * Only what it borrowed from — a strip listing everything
 * retrieval touched looks thorough and teaches a reader that
 * citations are not worth opening.
 *
 * Shown only when there is something to show. An empty strip
 * reads as "checked and found nothing", which is a different
 * claim from "did not need to look".
 */
export function Citations({
  cited,
  onOpen,
}: {
  cited: CitationRecord[] | undefined;
  onOpen?: (documentId: string) => void;
}) {
  const { t } = useTranslation();
  const described = describeCitations(cited);
  if (!described) return null;

  return (
    <div className="mt-2 border-t border-border/50 pt-2">
      <p className="mb-1 text-xs text-muted-foreground">{t('citations.heading')}</p>
      <ul className="flex flex-wrap gap-2">
        {described.map((citation) => (
          <li key={citation.documentId}>
            <button
              type="button"
              onClick={() => onOpen?.(citation.documentId)}
              aria-label={t('citations.open', { title: citation.title })}
              className="flex items-center gap-1.5 rounded border border-border px-2 py-1 text-xs hover:border-primary/60"
            >
              <FileText className="h-3 w-3 shrink-0 opacity-70" aria-hidden="true" />
              <span>{citation.title}</span>
              <span className="text-muted-foreground">
                {t(ORIGIN_KEY[citation.origin])}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
