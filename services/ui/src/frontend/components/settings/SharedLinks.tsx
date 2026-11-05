import { useTranslation } from 'react-i18next';
import { useCallback, useEffect, useState } from 'react';
import { Link2Off } from 'lucide-react';

import { presentShare } from '../../lib/share-view';
import { listShares, revokeShare, type Share } from '../../services/share-api';

/**
 * Everything this account has published.
 *
 * Without a list, the only way to find out what you have shared is to
 * remember — so expired links stay on it rather than disappearing.
 */
export function SharedLinks() {
  const { t } = useTranslation();
  const [shares, setShares] = useState<Share[] | null>(null);

  useEffect(() => {
    let alive = true;
    void listShares().then((found) => {
      if (alive) setShares(found);
    });
    return () => {
      alive = false;
    };
  }, []);

  const onRevoke = useCallback(async (share: Share) => {
    if (!share.threadId) return;
    if (await revokeShare(share.threadId)) {
      setShares((current) => (current ?? []).filter((one) => one.shareId !== share.shareId));
    }
  }, []);

  if (shares === null) {
    return null;
  }

  if (shares.length === 0) {
    return <p className="text-sm text-muted-foreground">{t('share.nothingShared')}</p>;
  }

  return (
    <ul className="list-none space-y-2">
      {shares.map((share) => {
        const presented = presentShare(
          {
            audience: share.scope === 'public' ? 'public' : 'signed-in',
            expiresAt: share.expiresAt ?? new Date(8.64e15).toISOString(),
            views: share.views,
            revoked: !share.active,
          } as never,
          new Date(),
        );

        return (
          <li
            key={share.shareId}
            className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card p-3"
          >
            <span className="min-w-0">
              <a
                href={share.path}
                className="block truncate text-sm text-foreground hover:underline"
              >
                {share.title || 'Untitled conversation'}
              </a>
              <span className="mt-0.5 flex flex-wrap gap-2 text-xs text-muted-foreground">
                <span>{presented.audience}</span>
                <span>{t(presented.views, { count: presented.viewsCount })}</span>
                <span>{t(presented.expiry, { count: presented.expiryCount })}</span>
              </span>
              {presented.warning && (
                <span className="mt-0.5 block text-xs text-amber-500">{presented.warning}</span>
              )}
            </span>
            {/* The presenter already works out that a revoked or
                expired link has nothing left to do to it; offering
                Revoke anyway said the link still worked. */}
            {presented.actions.includes('revoke') ? (
              <button
                type="button"
                onClick={() => void onRevoke(share)}
                className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs text-destructive transition-colors hover:bg-destructive/10"
              >
                <Link2Off className="h-3.5 w-3.5" />
                Revoke
              </button>
            ) : (
              <span className="shrink-0 text-xs text-muted-foreground">
                {t('share.noLongerWorks')}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
