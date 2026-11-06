import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Tag as TagIcon, X } from 'lucide-react';

import {
  getThreadTags,
  listTags,
  setThreadTags,
  type TagCount,
} from '../services/tags-api';

/** The tags on this conversation, and a way to change them. */
export function ThreadTags({ threadId }: { threadId: string }) {
  const { t } = useTranslation();
  const [tags, setTags] = useState<string[]>([]);
  const [known, setKnown] = useState<TagCount[]>([]);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState('');

  useEffect(() => {
    let alive = true;
    void getThreadTags(threadId).then((found) => {
      if (alive) setTags(found);
    });
    return () => {
      alive = false;
    };
  }, [threadId]);

  useEffect(() => {
    if (!adding) return;
    let alive = true;
    void listTags().then((found) => {
      if (alive) setKnown(found);
    });
    return () => {
      alive = false;
    };
  }, [adding]);

  // The agent replaces the whole set, so every change sends all of it.
  const save = useCallback(
    async (next: string[]) => {
      const settled = await setThreadTags(threadId, next);
      // A refusal leaves the conversation as it was rather than
      // showing a change that did not happen.
      if (settled !== null) setTags(settled);
    },
    [threadId],
  );

  const add = useCallback(
    (raw: string) => {
      const tag = raw.trim().toLowerCase();
      setDraft('');
      setAdding(false);
      // Nothing to ask the agent to refuse.
      if (!tag || tags.includes(tag)) return;
      void save([...tags, tag].sort());
    },
    [tags, save],
  );

  const suggestions = known.filter((count) => !tags.includes(count.tag));

  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <TagIcon className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground"
        >
          {tag}
          <button
            type="button"
            aria-label={`Remove ${tag}`}
            onClick={() => void save(tags.filter((one) => one !== tag))}
            className="text-muted-foreground hover:text-destructive"
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}

      {adding ? (
        <span className="inline-flex items-center gap-1">
          <input
            autoFocus
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') add(draft);
              if (event.key === 'Escape') {
                setDraft('');
                setAdding(false);
              }
            }}
            aria-label={t('tags.new')}
            className="w-28 rounded border border-border bg-transparent px-1.5 py-0.5 text-xs text-foreground outline-none focus:border-primary"
          />
          {suggestions.length > 0 && (
            <span role="listbox" aria-label={t('tags.inUse')} className="inline-flex gap-1">
              {suggestions.map((count) => (
                <button
                  key={count.tag}
                  type="button"
                  role="option"
                  aria-selected={false}
                  onClick={() => add(count.tag)}
                  className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  {/* The count is what tells a tag in real use from one
                      applied once and forgotten. */}
                  {count.tag} ({count.threads})
                </button>
              ))}
            </span>
          )}
        </span>
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="rounded-full border border-dashed border-border px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
        >
          {t('tags.add')}
        </button>
      )}
    </span>
  );
}
