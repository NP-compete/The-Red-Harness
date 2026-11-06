import { useEffect, useState } from 'react';
import { Alert } from '@patternfly/react-core';

import { buildAppPath } from '../../../lib/app-paths';
import { presentDrift, type DriftState } from '../../../lib/drift-view';

interface DriftReading {
  movement: DriftState['movement'];
  gap: number;
  outliers: string[];
}

/** Which way the suite has been going, against the agreed baseline. */
export function DriftBanner({ baseline = 0.8 }: { baseline?: number }) {
  const [reading, setReading] = useState<DriftReading | null>(null);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const res = await fetch(
          buildAppPath(`/api/proxy/agent/evals/drift?baseline=${baseline}`),
          { credentials: 'same-origin', signal: AbortSignal.timeout(10_000) },
        );
        if (!res.ok) return;
        const body = (await res.json()) as DriftReading;
        if (alive) setReading(body);
      } catch {
        // A missing reading is quieter than a wrong one.
      }
    })();
    return () => {
      alive = false;
    };
  }, [baseline]);

  if (!reading) {
    return null;
  }

  const drift = presentDrift({
    movement: reading.movement,
    gap: reading.gap,
    outliers: reading.outliers ?? [],
  });

  return (
    <Alert
      variant={drift.severity === 'high' ? 'danger' : 'info'}
      isInline
      title={drift.headline}
      className="mb-4"
    >
      {drift.detail}
      {drift.outlierNote ? <div>{drift.outlierNote}</div> : null}
    </Alert>
  );
}
