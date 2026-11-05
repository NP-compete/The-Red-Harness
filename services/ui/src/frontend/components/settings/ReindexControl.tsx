import { useTranslation } from 'react-i18next';
import { useCallback, useState } from 'react';
import { RefreshCw } from 'lucide-react';

import { reindexThreads } from '../../services/search-reindex';

/**
 * Rebuild the conversation search index.
 *
 * Searching reindexes on its own; this is for ruling the index out
 * when search is not finding something that ought to be there.
 */
export function ReindexControl() {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string>('');

  const run = useCallback(async () => {
    setBusy(true);
    setResult('');
    const indexed = await reindexThreads();
    setResult(
      indexed === null
        ? 'Could not rebuild the index just now'
        : indexed === 0
          ? 'Nothing to index'
          : t('counts.indexed', { count: indexed }),
    );
    setBusy(false);
  }, []);

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        disabled={busy}
        onClick={() => void run()}
        className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40"
      >
        <RefreshCw className={`h-3.5 w-3.5 ${busy ? 'animate-spin' : ''}`} />
        {t('documents.rebuildIndex')}</button>
      {result && <span className="text-xs text-muted-foreground">{result}</span>}
    </div>
  );
}
