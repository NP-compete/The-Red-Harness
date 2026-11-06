import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { presentHistory } from '../../lib/config-history-view';
import {
  readConfigHistory,
  readEditingState,
  revertConfig,
  type StoredVersion,
} from '../../services/config-editing-api';

interface Props {
  path: string;
}

/**
 * What this file used to say, and who changed it.
 *
 * The question behind this screen is almost always "why is it
 * like this", asked by somebody who did not do it — so each
 * version carries a name and a time, and can be put back
 * without retyping.
 *
 * Restoring adds a version rather than removing the ones after
 * it, and that is said before anything is pressed. Otherwise
 * "restore" reads as "delete what I did since", and somebody
 * hesitates over the one action that is safe.
 */
export function ConfigHistory({ path }: Props) {
  const { t } = useTranslation();
  const [versions, setVersions] = useState<StoredVersion[] | null | undefined>(
    undefined,
  );
  const [editable, setEditable] = useState(false);
  const [refused, setRefused] = useState('');

  const reload = useCallback(async () => {
    setVersions(await readConfigHistory(path));
  }, [path]);

  useEffect(() => {
    let live = true;
    void Promise.all([readConfigHistory(path), readEditingState()]).then(
      ([found, state]) => {
        if (!live) return;
        setVersions(found);
        setEditable(state?.editable === true);
      },
    );
    return () => {
      live = false;
    };
  }, [path]);

  const onRestore = useCallback(
    async (version: number) => {
      setRefused('');
      const found = await revertConfig(path, version);
      if (!found.ok) {
        setRefused(found.detail ?? '');
        return;
      }
      await reload();
    },
    [path, reload],
  );

  // Still asking, or could not ask. Saying "no changes" for
  // either would be an answer nobody gave.
  if (versions === undefined || versions === null) return null;

  const shown = presentHistory(versions, new Date());

  if (shown.count === 0) {
    return <p className="text-sm text-muted-foreground">{shown.emptyMessage}</p>;
  }

  return (
    <div>
      <p className="mb-2 text-xs text-muted-foreground">{shown.restoreNote}</p>
      <ul className="space-y-2">
        {shown.rows.map((row) => (
          <li
            key={row.version}
            className="flex items-center justify-between rounded border border-border px-3 py-2"
          >
            <span className="text-sm">
              {t('history.version', { version: row.version })} — {row.by}
              {row.summary && ` — ${row.summary}`}
              {row.current && ` — ${t('history.inForce')}`}
            </span>
            {editable && row.canRestore && (
              <button
                type="button"
                onClick={() => void onRestore(row.version)}
                className="rounded border border-border px-3 py-1 text-sm"
              >
                {t('history.restore')}
              </button>
            )}
          </li>
        ))}
      </ul>
      {refused && (
        <p className="mt-3 text-xs text-destructive" role="alert">
          {refused}
        </p>
      )}
    </div>
  );
}
