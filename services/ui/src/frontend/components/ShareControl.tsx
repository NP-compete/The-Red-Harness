import { useTranslation } from 'react-i18next';
import { useCallback, useEffect, useState } from 'react';
import { Link2, Link2Off } from 'lucide-react';

import { presentShare } from '../lib/share-view';
import { createShare, getShare, revokeShare, type Share } from '../services/share-api';

/** Long enough to be read and discussed, short enough to go stale. */
const DEFAULT_DAYS = 7;

/** Whether this conversation is behind a link, and what that link allows. */
export function ShareControl({ threadId }: { threadId: string }) {
  const { t } = useTranslation();
  const [share, setShare] = useState<Share | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    void getShare(threadId).then((found) => {
      if (alive) setShare(found);
    });
    return () => {
      alive = false;
    };
  }, [threadId]);

  const onShare = useCallback(async () => {
    setBusy(true);
    setShare(await createShare(threadId, 'authenticated', DEFAULT_DAYS));
    setBusy(false);
  }, [threadId]);

  const onRevoke = useCallback(async () => {
    setBusy(true);
    if (await revokeShare(threadId)) {
      setShare(null);
    }
    setBusy(false);
  }, [threadId]);

  if (!share || !share.active) {
    return (
      <button
        type="button"
        disabled={busy}
        onClick={onShare}
        className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40"
      >
        <Link2 className="h-3.5 w-3.5" />
        {t('common.share')}
      </button>
    );
  }

  const presented = presentShare(
    {
      scope: share.scope,
      audience: share.scope === 'public' ? 'public' : 'signed-in',
      // A link with no end is reported as one: the view decides what
      // to say about it, rather than a date being invented here.
      expiresAt: share.expiresAt ?? new Date(8.64e15).toISOString(),
      views: share.views,
      revoked: !share.active,
    } as never,
    new Date(),
  );

  return (
    <span className="inline-flex items-center gap-2 text-xs">
      <span className="text-muted-foreground">{presented.audience}</span>
      <span className="text-muted-foreground">{t(presented.views, { count: presented.viewsCount })}</span>
      <span className="text-muted-foreground">{t(presented.expiry, { count: presented.expiryCount })}</span>
      {presented.warning && <span className="text-amber-500">{presented.warning}</span>}
      <button
        type="button"
        disabled={busy}
        onClick={onRevoke}
        className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-destructive transition-colors hover:bg-destructive/10 disabled:opacity-40"
      >
        <Link2Off className="h-3.5 w-3.5" />
        Revoke
      </button>
    </span>
  );
}
