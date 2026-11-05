import { useEffect, useState } from 'react';
import { Alert } from '@patternfly/react-core';

import { buildAppPath } from '../../lib/app-paths';
import { presentErrorBudget, type BudgetState } from '../../lib/error-budget-view';

interface BudgetReading {
  state: BudgetState['state'];
  used: number;
  failures_left: number;
  may_deploy: boolean;
  warn: boolean;
  exceptional: boolean;
  reason: string;
}

/** How much of the allowed failure this window has already spent. */
export function ErrorBudgetCard({ days = 7 }: { days?: number }) {
  const [reading, setReading] = useState<BudgetReading | null>(null);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const res = await fetch(
          buildAppPath(`/api/proxy/agent/analytics/error-budget?days=${days}`),
          { credentials: 'same-origin', signal: AbortSignal.timeout(10_000) },
        );
        if (!res.ok) return;
        const body = (await res.json()) as BudgetReading;
        if (alive) setReading(body);
      } catch {
        // A missing reading is quieter than a wrong one.
      }
    })();
    return () => {
      alive = false;
    };
  }, [days]);

  if (!reading) {
    return null;
  }

  const budget = presentErrorBudget({
    state: reading.state,
    used: reading.used,
    failuresLeft: reading.failures_left,
    mayDeploy: reading.may_deploy,
    warn: reading.warn,
    exceptional: reading.exceptional,
    reason: reading.reason,
  });

  return (
    <Alert
      variant={
        budget.severity === 'high' ? 'danger' : budget.severity === 'medium' ? 'warning' : 'info'
      }
      isInline
      title={budget.headline}
      className="mb-4"
    >
      {budget.detail}
      {reading.reason ? <div>{reading.reason}</div> : null}
      {budget.note ? <div>{budget.note}</div> : null}
    </Alert>
  );
}
