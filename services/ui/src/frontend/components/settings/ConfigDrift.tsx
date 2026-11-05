import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { summariseDrift, type ConfigFile } from '../../lib/config-drift';
import { ConfigHistory } from './ConfigHistory';
import {
  adoptBaseline,
  exportPath,
  readConfigDrift,
  readEditingState,
} from '../../services/config-editing-api';

/**
 * What this deployment has changed about itself.
 *
 * Editing configuration here means a change to the same path in
 * the pipeline stops arriving. That cost is invisible from
 * either side — the repository says one thing, the agent does
 * another, and each looks correct on its own — so this screen
 * is the only place it can be seen.
 *
 * Which makes the empty state the one to get right. "Nothing
 * has drifted" and "I could not ask" must not look alike: the
 * first is reassurance and the second is a question nobody
 * answered, and reassurance nobody earned is worse than
 * silence.
 */
export function ConfigDrift() {
  const { t } = useTranslation();
  const [files, setFiles] = useState<ConfigFile[] | null | undefined>(undefined);
  const [editable, setEditable] = useState(false);
  const [refused, setRefused] = useState('');

  const reload = useCallback(async () => {
    setFiles(await readConfigDrift());
  }, []);

  useEffect(() => {
    let live = true;
    void Promise.all([readConfigDrift(), readEditingState()]).then(
      ([drift, state]) => {
        if (!live) return;
        setFiles(drift);
        setEditable(state?.editable === true);
      },
    );
    return () => {
      live = false;
    };
  }, []);

  const onAdopt = useCallback(
    async (path: string) => {
      setRefused('');
      const found = await adoptBaseline(path);
      if (!found.ok) {
        // The agent's own words: it knows whether this is a
        // read-only deployment or a missing store, and those
        // have different answers.
        setRefused(found.detail ?? '');
        return;
      }
      await reload();
    },
    [reload],
  );

  // Still asking, or could not ask. Neither is "nothing has
  // drifted", and saying so would be reassurance nobody earned.
  if (files === undefined || files === null) return null;

  const shown = summariseDrift(files, { readOnly: !editable });

  return (
    <section className="mb-12">
      <h2 className="mb-2 text-base font-semibold">{t('drift.heading')}</h2>

      {shown.count === 0 ? (
        <p className="text-sm text-muted-foreground">{t('drift.none')}</p>
      ) : (
        <>
          <p className="mb-3 text-sm text-amber-500/90" role="status">
            {shown.warning}
          </p>
          <ul className="space-y-4">
            {shown.rows.map((row) => (
              <li key={row.path} className="rounded border border-border p-3">
                <p className="font-mono text-sm">{row.path}</p>
                {row.author && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t('drift.changedBy', { author: row.author, at: row.at ?? '' })}
                  </p>
                )}
                <div className="mt-2 grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="mb-1 text-xs text-muted-foreground">
                      {t('drift.baseline')}
                    </p>
                    <pre className="overflow-x-auto rounded bg-card p-2 text-xs">
                      {row.baseline ?? t('drift.noBaseline')}
                    </pre>
                  </div>
                  <div>
                    <p className="mb-1 text-xs text-muted-foreground">
                      {t('drift.current')}
                    </p>
                    <pre className="overflow-x-auto rounded bg-card p-2 text-xs">
                      {row.current}
                    </pre>
                  </div>
                </div>
                <div className="mt-3">
                  <ConfigHistory path={row.path} />
                </div>
                <div className="mt-2 flex items-center gap-3">
                  {row.actions.includes('adopt-baseline') && (
                    <button
                      type="button"
                      onClick={() => void onAdopt(row.path)}
                      className="rounded border border-border px-3 py-1 text-sm"
                    >
                      {t('drift.adopt')}
                    </button>
                  )}
                  {row.actions.includes('export') && (
                    <a
                      href={exportPath()}
                      className="text-sm underline underline-offset-2"
                    >
                      {t('drift.export')}
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      {refused && (
        <p className="mt-3 text-xs text-destructive" role="alert">
          {refused}
        </p>
      )}
    </section>
  );
}
