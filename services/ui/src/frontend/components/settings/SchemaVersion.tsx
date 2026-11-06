import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';

import { describeSchema, type SchemaWindow } from '../../lib/schema-view';
import { readSchemaWindow } from '../../services/schema-version-api';

/**
 * Which configuration layout this pod reads, and which one it was given.
 *
 * Shown together because neither is useful alone: a tree declaring
 * version 2 starts on one image and is refused by the next, and the
 * only way to know which is to see the window beside it. The question
 * gets asked during an upgrade, when the answer is hardest to get.
 */
export function SchemaVersion() {
  const { t } = useTranslation();
  const [found, setFound] = useState<SchemaWindow | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    void readSchemaWindow().then((window) => {
      if (live) setFound(window);
    });
    return () => {
      live = false;
    };
  }, []);

  if (found === undefined) return null;
  const described = describeSchema(found);
  if (!described) return null;

  return (
    <div
      className="mt-2 flex items-center gap-2"
      // A status only when it is one. Every healthy deployment
      // announcing itself is how the one that mattered gets missed.
      {...(described.ageing ? { role: 'status' as const } : {})}
    >
      <span className="text-sm text-muted-foreground">
        {t('schemaVersion.label')}
      </span>
      <code className="rounded bg-muted px-2 py-1 text-sm font-medium">
        {described.declared ?? t('schemaVersion.absent')}
      </code>
      <span className="text-xs text-muted-foreground">
        {t('schemaVersion.accepts', { versions: described.accepts })}
      </span>
      {described.ageing ? (
        <span className="flex items-center gap-1 text-xs text-amber-500">
          <AlertTriangle className="h-3 w-3" aria-hidden="true" />
          {t('schemaVersion.ageing')}
        </span>
      ) : null}
    </div>
  );
}
