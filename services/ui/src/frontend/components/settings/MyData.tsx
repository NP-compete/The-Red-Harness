import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Download } from 'lucide-react';

import {
  deleteMyData,
  exportHref,
  previewDeletion,
  type DeletionPreview,
  type DeletionResult,
} from '../../services/my-data-api';

function total(counts: Record<string, number>): number {
  return Object.values(counts).reduce((sum, n) => sum + n, 0);
}

function names(of: Record<string, string[]>): string[] {
  return Object.entries(of)
    .filter(([, ids]) => ids.length)
    .map(([section]) => section);
}

/**
 * Taking a copy of what is held, and asking for it to go.
 *
 * Shown before it is done, because deletion is the one action
 * nobody can undo by asking again: what would go, what would
 * survive, and what is kept whatever anybody asks. Then a
 * confirmation, because one click away from irreversible is a
 * reflex rather than a decision.
 */
export function MyData() {
  const { t } = useTranslation();
  const [preview, setPreview] = useState<DeletionPreview | null | undefined>(
    undefined,
  );
  const [asking, setAsking] = useState(false);
  const [done, setDone] = useState<DeletionResult | null>(null);

  useEffect(() => {
    let live = true;
    void previewDeletion().then((found) => {
      if (live) setPreview(found);
    });
    return () => {
      live = false;
    };
  }, []);

  if (preview === undefined || preview === null) return null;

  const going = total(preview.counts);
  const surviving = names(preview.kept);
  // What this action does not reach. The label has to match
  // what the button does: somebody reading "delete
  // everything" will believe memory went with it.
  const uncovered = Object.entries(preview.not_included ?? {});
  const failed = done ? Object.keys(done.failed ?? {}) : [];

  return (
    <div className="mt-6 border-t border-border pt-4">
      <h3 className="text-sm font-medium">{t('myData.heading')}</h3>

      <a
        data-testid="take-a-copy"
        href={exportHref()}
        download
        className="mt-3 inline-flex items-center gap-1.5 rounded border border-border px-2 py-1 text-xs hover:border-primary/60"
      >
        <Download className="h-3 w-3 shrink-0 opacity-70" aria-hidden="true" />
        {t('myData.takeACopy')}
      </a>

      <p className="mt-3 text-xs text-muted-foreground">
        {t('myData.wouldGo', { count: going })}
      </p>
      {surviving.length ? (
        // Said before they ask. Shared content belongs to the
        // team as much as to whoever happened to add it.
        <p className="mt-1 text-xs text-muted-foreground">
          {t('myData.wouldStay', { sections: surviving.join(', ') })}
        </p>
      ) : null}
      {uncovered.map(([store, why]) => (
        <p key={store} className="mt-1 text-xs text-muted-foreground">
          {t('myData.notIncluded', { store, why })}
        </p>
      ))}
      {preview.notes.map((note) => (
        <p key={note} className="mt-1 text-xs text-muted-foreground">
          {note}
        </p>
      ))}

      {asking ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs">{t('myData.sure', { count: going })}</span>
          <button
            type="button"
            data-testid="confirm-delete"
            onClick={() => {
              setAsking(false);
              void deleteMyData().then(setDone);
            }}
            className="rounded bg-destructive px-2 py-1 text-xs text-destructive-foreground"
          >
            {t('myData.confirm')}
          </button>
          <button
            type="button"
            data-testid="cancel-delete"
            onClick={() => setAsking(false)}
            className="rounded border border-border px-2 py-1 text-xs"
          >
            {t('myData.cancel')}
          </button>
        </div>
      ) : (
        <button
          type="button"
          data-testid="delete-everything"
          onClick={() => setAsking(true)}
          className="mt-3 rounded border border-destructive/60 px-2 py-1 text-xs text-destructive"
        >
          {uncovered.length
            ? t('myData.deleteMost')
            : t('myData.deleteEverything')}
        </button>
      )}

      {done && failed.length ? (
        // Said plainly. Reporting success for a deletion that
        // did not happen is the one outcome nobody recovers
        // from, because they stop asking.
        <p
          role="alert"
          className="mt-2 flex items-center gap-1 text-xs text-amber-500"
        >
          <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
          {t('myData.couldNot', { sections: failed.join(', ') })}
        </p>
      ) : null}
      {done && !failed.length ? (
        <p role="status" className="mt-2 text-xs text-muted-foreground">
          {t('myData.went', { count: total(done.counts ?? {}) })}
        </p>
      ) : null}
    </div>
  );
}
