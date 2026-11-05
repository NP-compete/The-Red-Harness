import { useMemo } from 'react';
import { Alert } from '@patternfly/react-core';

import { scanOutgoing } from '../lib/scan-outgoing';
import { presentSecretWarning } from '../lib/secret-warning-view';

/** A quiet word before a credential is sent into a conversation. */
export function SecretWarning({ text }: { text: string }) {
  const warning = useMemo(() => {
    if (!text.trim()) return null;
    return presentSecretWarning(scanOutgoing(text));
  }, [text]);

  if (!warning) {
    return null;
  }

  return (
    <Alert
      variant="warning"
      isInline
      title={warning.headline}
      role="status"
      aria-live="polite"
      className="mb-1"
    >
      {/* Where to look, never the credential itself. */}
      {warning.locations.join(', ')}
    </Alert>
  );
}
