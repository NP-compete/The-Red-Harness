import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronRight, Scissors } from 'lucide-react';

/**
 * Where a long conversation was shortened.
 *
 * The turns before this point are no longer being sent to the agent;
 * what it has instead is the summary below. Saying so is the
 * difference between a conversation that was pruned and an agent
 * that appears to have forgotten.
 */
export function CompactionNote({ summary }: { summary: string }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const Chevron = open ? ChevronDown : ChevronRight;

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        <Scissors className="h-3 w-3" aria-hidden="true" />
        <span>{t('chat.compactedDivider')}</span>
        <span className="h-px flex-1 bg-border" />
      </div>
      {summary && (
        <>
          <button
            type="button"
            onClick={() => setOpen((was) => !was)}
            aria-expanded={open}
            className="mx-auto mt-1 flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            <Chevron className="h-3 w-3" aria-hidden="true" />
            {open ? 'Hide what was kept' : 'Read what was kept'}
          </button>
          {open && (
            <p className="mt-2 whitespace-pre-wrap rounded-lg border border-border bg-card p-3 text-xs text-foreground">
              {summary}
            </p>
          )}
        </>
      )}
    </div>
  );
}
