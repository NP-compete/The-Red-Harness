import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Download } from 'lucide-react';

import { buildAgentApiUrl } from '../lib/app-paths';

/**
 * The numbers on this page, as a file.
 *
 * A dashboard answers "how are we doing". The question behind an
 * export is usually somebody else's — what did this cost, split
 * how — and the only route there today is reading the screen and
 * retyping it.
 */
export function ExportButton({ what, days }: { what: string; days: number }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const save = async () => {
    if (busy) return;
    setBusy(true);
    setFailed(false);
    try {
      const response = await fetch(
        buildAgentApiUrl(`/analytics/export?what=${encodeURIComponent(what)}&days=${days}`),
      );
      if (!response.ok) {
        // No file. An empty spreadsheet reads as "no usage",
        // which is a different answer from "this did not work".
        setFailed(true);
        return;
      }
      const url = URL.createObjectURL(await response.blob());
      try {
        const link = document.createElement('a');
        link.href = url;
        link.download = `${what}-${days}d.csv`;
        link.click();
      } finally {
        // Otherwise every export holds a file in memory until the
        // tab closes.
        URL.revokeObjectURL(url);
      }
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => void save()}
        disabled={busy}
        className="inline-flex items-center gap-1.5 rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/60 disabled:opacity-50"
      >
        <Download className="h-3.5 w-3.5" aria-hidden="true" />
        {t('analytics.export')}
      </button>
      {failed && (
        <span role="alert" className="ml-2 text-xs text-destructive">
          {t('analytics.exportFailed')}
        </span>
      )}
    </>
  );
}
