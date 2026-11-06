import { useCallback, useEffect, useState } from 'react';

import { listTags, threadsWithTag, type TagCount } from '../services/tags-api';

interface TagFilterProps {
  /** The chosen tag and the conversations carrying it, or `null` for none. */
  onFilter: (tag: string | null, threadIds: string[] | null) => void;
}

/** Narrow the conversation list to one tag. */
export function TagFilter({ onFilter }: TagFilterProps) {
  const [tags, setTags] = useState<TagCount[]>([]);
  const [chosen, setChosen] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void listTags().then((found) => {
      if (alive) {
        // Most used first: a tag applied once is noise beside one
        // applied forty times.
        setTags([...found].sort((a, b) => b.threads - a.threads));
      }
    });
    return () => {
      alive = false;
    };
  }, []);

  const choose = useCallback(
    async (tag: string) => {
      if (chosen === tag) {
        // Clearing needs nothing from the agent.
        setChosen(null);
        onFilter(null, null);
        return;
      }
      setChosen(tag);
      const found = await threadsWithTag(tag);
      onFilter(
        tag,
        found.map((thread) => thread.id),
      );
    },
    [chosen, onFilter],
  );

  if (tags.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-1 px-3 pb-2">
      {tags.map((count) => (
        <button
          key={count.tag}
          type="button"
          aria-pressed={chosen === count.tag}
          onClick={() => void choose(count.tag)}
          className={`rounded-full border px-2 py-0.5 text-[11px] transition-colors ${
            chosen === count.tag
              ? 'border-primary bg-primary/10 text-primary'
              : 'border-border text-muted-foreground hover:text-foreground'
          }`}
        >
          {count.tag} {count.threads}
        </button>
      ))}
    </div>
  );
}
