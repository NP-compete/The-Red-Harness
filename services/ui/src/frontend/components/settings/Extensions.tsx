import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { extensionCost } from '../../lib/extension-cost';
import { listExtensions, type Extension } from '../../services/extensions-api';

/**
 * Middleware this deployment has interposed on its runs.
 *
 * An extension runs inside the agent with the agent's privileges
 * and can change what a person is shown, so which ones are in the
 * path is not something to have to read the configuration to learn.
 */
export function Extensions() {
  const { t } = useTranslation();
  const [found, setFound] = useState<Extension[] | null>(null);
  const [asked, setAsked] = useState(false);

  useEffect(() => {
    let alive = true;
    void listExtensions().then((list) => {
      if (!alive) return;
      setFound(list);
      setAsked(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (!asked || found === null) {
    return null;
  }

  if (found.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {t('extensions.none')}
      </p>
    );
  }

  return (
    <ul className="list-none space-y-2">
      {found.map((one) => (
        <li key={one.path} className="rounded-lg border border-border bg-card p-3">
          <code className="text-sm text-foreground">{one.path}</code>
          <p className="text-xs text-muted-foreground">
            {one.loaded ? t('extensions.inPath') : t('extensions.notLoaded')} ·{' '}
            {one.required ? t('extensions.required') : t('extensions.optional')}
          </p>
          {one.problem && <p className="text-xs text-destructive">{one.problem}</p>}
          {one.timing && (
            <p className="text-xs tabular-nums text-muted-foreground">
              {extensionCost(one.timing)}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
