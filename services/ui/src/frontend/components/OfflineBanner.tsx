import { Alert, AlertActionLink } from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';

import { presentOfflineBanner } from '@/lib/offline-banner-view';
import { useConnectionState } from '../hooks/useConnectionState';

interface OfflineBannerProps {
  queued?: number;
  runInFlight?: boolean;
}

export function OfflineBanner({ queued = 0, runInFlight = false }: OfflineBannerProps) {
  const { t } = useTranslation();
  const link = useConnectionState();

  const banner = presentOfflineBanner({
    connected: link.connected,
    warn: link.warn,
    queued,
    runOutcomeUnknown: !link.connected && runInFlight,
    secondsDown: link.secondsDown,
  });

  if (!banner) {
    return null;
  }

  return (
    <Alert
      variant={banner.severity === 'high' ? 'danger' : 'warning'}
      isInline
      title={t(banner.headline)}
      role="status"
      aria-live="polite"
      actionLinks={
        <AlertActionLink onClick={() => window.location.reload()}>
          {t(banner.actions[0])}
        </AlertActionLink>
      }
    >
      {banner.detail ? t(banner.detail, { count: banner.queued }) : null}
      {banner.warning ? <div>{t(banner.warning)}</div> : null}
    </Alert>
  );
}
