import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';

import {
  getExtractionStatus,
  type ExtractionStatus as Status,
} from '../../services/extraction-status';
import { Trans, useTranslation } from 'react-i18next';

function size(bytes: number): string {
  // Stated the way the limit is configured — a 20 MiB cap reads as
  // 21 MB in round millions, which looks like a different number.
  const mb = bytes / (1024 * 1024);
  return `${Number.isInteger(mb) ? mb : mb.toFixed(1)} MB`;
}

/** What reads an attachment, and whether it is working. */
export function ExtractionStatus() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    let alive = true;
    void getExtractionStatus().then((found) => {
      if (alive) setStatus(found);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (!status) {
    return null;
  }

  return (
    <div className="space-y-2 text-sm">
      <p className="text-muted-foreground">
        <Trans
          i18nKey="settings.extractionReadBy"
          values={{
            engine: status.engine,
            limit: status.maxBytes > 0 ? `, up to ${size(status.maxBytes)} each` : '',
          }}
          components={[<span key="0" />, <code key="1" className="text-foreground" />]}
        />
      </p>
      {status.handles.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {t('settings.extractionHandles', { kinds: status.handles.join(', ') })}
        </p>
      )}
      {/* The reason a file came back unread is either this or the
          file itself, and only one of them is worth checking first. */}
      {!status.reachable && (
        <p className="flex items-start gap-1.5 text-amber-600 dark:text-amber-500">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
          <span>
            {t('settings.extractionUnreachable')}{status.detail}
          </span>
        </p>
      )}
      <p className="text-xs text-muted-foreground">
        {status.fallback
          ? 'A file it cannot read is passed to the built-in parsers instead.'
          : 'A file it cannot read will not be read at all.'}
      </p>
    </div>
  );
}
