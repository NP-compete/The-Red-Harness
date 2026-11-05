import { Alert } from '@patternfly/react-core';

import { presentDataset } from '../../lib/dataset-view';

// Below this, one case landing differently moves the score more than a
// real change would.
const ENOUGH_CASES = 10;

/** Whether this dataset can answer the question it is asked. */
export function DatasetHealth({ caseCount }: { caseCount: number }) {
  if (caseCount === 0) {
    return null;
  }

  const dataset = presentDataset({
    count: caseCount,
    // Every case is used for tuning: this suite holds nothing back,
    // which is a fact about it rather than a setting.
    workingCount: caseCount,
    holdoutCount: 0,
    excluded: {},
    tooSmall: caseCount < ENOUGH_CASES,
  });

  return (
    <Alert
      variant={dataset.usable ? 'info' : 'warning'}
      isInline
      title={dataset.headline}
      className="mb-4"
    >
      {dataset.warning}
    </Alert>
  );
}
