import { useSyncExternalStore, type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { Spinner } from '@patternfly/react-core';

import { isPrivilegedUser, onPrivilegeKnown, privilegeKnown } from '../lib/role-utils';
import { useTranslation } from 'react-i18next';

/**
 * A page only operators may open.
 *
 * Waits for the answer rather than guessing: with sign-in off the
 * deciding flag arrives with the configuration, and turning an allowed
 * reader away in that moment is worse than a spinner.
 */
export function RequirePrivilege({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  // Re-renders this gate the moment the answer becomes knowable.
  const known = useSyncExternalStore(onPrivilegeKnown, privilegeKnown, privilegeKnown);

  if (!known) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" aria-label={t('common.checkingAccess')} />
      </div>
    );
  }

  return isPrivilegedUser() ? <>{children}</> : <Navigate to="/" replace />;
}
