import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';

import {
  getApprovalPolicy,
  type ApprovalPolicy as Policy,
  type Decision,
} from '../../services/permissions-api';
import { useTranslation } from 'react-i18next';

const SAYS: Record<Decision, string> = {
  allow: 'safeguards.verdictAllow',
  ask: 'safeguards.verdictAsk',
  refuse: 'safeguards.verdictRefuse',
};

const RISK_STYLE = {
  low: 'border-border text-muted-foreground',
  medium: 'border-amber-500/40 text-amber-600 dark:text-amber-500',
  high: 'border-red-500/40 text-red-600 dark:text-red-500',
} as const;

/**
 * What this deployment lets the agent do unattended.
 *
 * The always-allowed list below is what one person added on top; this
 * is the floor it sits on, and without it "why did it ask me that?"
 * had no answer anywhere.
 */
export function ApprovalPolicy() {
  const { t } = useTranslation();
  const [policy, setPolicy] = useState<Policy | null>(null);

  useEffect(() => {
    let alive = true;
    void getApprovalPolicy().then((found) => {
      if (alive) setPolicy(found);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (!policy) {
    return null;
  }

  return (
    <div className="space-y-3">
      {!policy.enabled && (
        <p className="flex items-start gap-1.5 text-sm text-amber-600 dark:text-amber-500">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
          {t('safeguards.approvalsOff')}</p>
      )}
      <ul className="list-none space-y-2">
        {policy.rules.map((rule) => (
          <li
            key={rule.tools.join(',')}
            className="rounded-lg border border-border bg-card p-3"
          >
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
              <code className="text-sm text-foreground">{rule.tools.join(', ')}</code>
              <span
                className={`rounded-full border px-2 py-0.5 text-xs ${RISK_STYLE[rule.risk]}`}
              >
                {SAYS[rule.decision]}
              </span>
            </div>
            {rule.reason && (
              <p className="mt-1 text-xs text-muted-foreground">{rule.reason}</p>
            )}
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        {t('safeguards.anythingElse', { verdict: t(SAYS[policy.otherwise]) })}
      </p>
      {!policy.live && (
        <p className="text-sm text-muted-foreground">
          {t('safeguards.runningDry')}</p>
      )}
      {policy.workspace.length > 0 && (
        <ul className="list-none space-y-1 border-t border-border pt-3">
          {policy.workspace.map((rule) => (
            <li
              key={`${rule.allowed}-${rule.paths.join(',')}`}
              className="text-xs text-muted-foreground"
            >
              {rule.allowed ? 'May ' : 'May not '}
              {rule.operations.join(', ') || 'touch'} in{' '}
              <code className="text-foreground">{rule.paths.join(', ')}</code>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
