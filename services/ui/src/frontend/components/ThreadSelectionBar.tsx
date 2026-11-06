import { useTranslation } from 'react-i18next';
import { Trash2 } from 'lucide-react';

interface ThreadSelectionBarProps {
  count: number;
  summary: string;
  beyondThisPage: boolean;
  onSelectAll: () => void;
  onClear: () => void;
  onDelete: () => void;
}

/** What is picked, and what can be done with it. */
export function ThreadSelectionBar({
  count,
  summary,
  beyondThisPage,
  onSelectAll,
  onClear,
  onDelete,
}: ThreadSelectionBarProps) {
  const { t } = useTranslation();
  if (count === 0) {
    return null;
  }

  return (
    <div className="mx-2 mb-2 rounded-lg border border-border bg-card p-2">
      <span className="block text-xs text-foreground">{summary}</span>
      <div className="mt-1.5 flex flex-wrap items-center gap-1">
        <div className="flex flex-wrap items-center gap-1">
          {!beyondThisPage && (
            <button
              type="button"
              className="rounded px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
              onClick={onSelectAll}
            >
              {t('threads.selectAll')}
            </button>
          )}
          <button
            type="button"
            className="rounded px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
            onClick={onClear}
          >
            {t('common.cancel')}
          </button>
          <button
            type="button"
            className="flex items-center gap-1 rounded bg-destructive/10 px-2 py-1 text-xs text-destructive hover:bg-destructive/20"
            onClick={onDelete}
          >
            <Trash2 className="h-3 w-3" />
            Delete {count}
          </button>
        </div>
      </div>
      {/* A selection that reaches past the screen is the one people
          regret, so it says so before the button is pressed. */}
      {beyondThisPage && (
        <p className="mt-1 text-[11px] text-amber-500">
          {t('threads.includesHidden')}
        </p>
      )}
    </div>
  );
}
