import { useTranslation } from 'react-i18next';
import { parseSnippet, type ThreadSearchHit } from '../services/search-api';
import { sayWhen } from '../lib/say-size';
import { whenLastActive } from '../lib/when';

interface SearchResultsProps {
  hits: ThreadSearchHit[];
  loading: boolean;
  error: string | null;
  /** Threads the sidebar's own title filter already shows. */
  excludeIds: Set<string>;
  onSelect: (threadId: string) => void;
}

/**
 * Conversations whose *content* matched, shown under the sidebar's
 * title matches.
 *
 * Kept separate rather than merged into one list: a title match and a
 * body match are different kinds of answer, and interleaving them by
 * rank buries the thread the user was probably looking for.
 */
export function SearchResults({
  hits,
  loading,
  error,
  excludeIds,
  onSelect,
}: SearchResultsProps) {
  const { t, i18n } = useTranslation();
  const extra = hits.filter((hit) => !excludeIds.has(hit.thread_id));

  if (loading) {
    return (
      <p className="px-3 py-2 text-xs text-muted-foreground" role="status">
        {t('search.searching')}
      </p>
    );
  }

  if (error) {
    // Local title filtering still works, so this is a degraded result,
    // not a dead end — say which half failed.
    return (
      <p className="px-3 py-2 text-xs text-muted-foreground" role="status">
        {t('search.titlesOnly')}
      </p>
    );
  }

  if (extra.length === 0) return null;

  return (
    <div className="mb-2">
      <p className="px-3 pt-3 pb-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
        {t('search.foundIn')}
      </p>
      <ul className="px-1.5 space-y-0.5 list-none" aria-label={t('search.contentResults')}>
        {extra.map((hit) => (
          <li key={hit.thread_id}>
            <button
              type="button"
              onClick={() => onSelect(hit.thread_id)}
              className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-secondary/50 transition-colors"
            >
              <div className="flex items-baseline justify-between gap-2">
                <p className="truncate text-sm text-foreground">
                  {hit.title || 'Untitled conversation'}
                </p>
                {/* Two conversations about the same thing are told
                    apart by which one is recent, and nothing else on
                    this row says. */}
                {sayWhen(whenLastActive(hit.updated_at), t, i18n.language) && (
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {sayWhen(whenLastActive(hit.updated_at), t, i18n.language)}
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {/* Rendered as text nodes, never dangerouslySetInnerHTML:
                    the snippet is the user's own message content and
                    would be a stored-XSS vector as markup. */}
                {parseSnippet(hit.snippet).map((part, index) =>
                  part.match ? (
                    <mark key={index} className="bg-primary/20 text-foreground rounded px-0.5">
                      {part.text}
                    </mark>
                  ) : (
                    <span key={index}>{part.text}</span>
                  ),
                )}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
