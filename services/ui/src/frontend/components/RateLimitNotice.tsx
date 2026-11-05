import { Alert } from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';

import { presentRateLimit } from '../lib/rate-limit-view';

interface RateLimitNoticeProps {
  isRateLimited: boolean;
  retryAfterSeconds: number;
}

/** Why a message cannot go yet, and when it can. */
export function RateLimitNotice({ isRateLimited, retryAfterSeconds }: RateLimitNoticeProps) {
  const { t } = useTranslation();
  const limit = presentRateLimit({
    allowed: !isRateLimited,
    // How much headroom is left is not reported to the browser, so the
    // quieter "slow down" warning has nothing to stand on.
    remaining: Number.MAX_SAFE_INTEGER,
    burst: 0,
    retryAfter: retryAfterSeconds,
    reason: '',
  });

  if (!limit) {
    return null;
  }

  return (
    <Alert
      variant={limit.severity === 'high' ? 'warning' : 'info'}
      isInline
      title={t(limit.headline, { count: limit.count })}
      role="status"
      aria-live="polite"
      className="mb-1"
    >
      {limit.detail ? t(limit.detail, { count: limit.count }) : null}
    </Alert>
  );
}
