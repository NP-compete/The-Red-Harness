export interface Failure {
  message: string;
  detail: string;
  reference: string;
  retryable: boolean;
}

export interface FailureViewer {
  isOperator: boolean;
}

export interface PresentedFailure {
  message: string;
  detail: string;
  hasDetail: boolean;
  detailOpen: false;
  reference: string;
  referenceNote: string;
  succeeded: false;
  action: 'retry' | 'report';
}

const FALLBACK = 'Something went wrong while running this step.';

export function presentFailure(failure: Failure, viewer: FailureViewer): PresentedFailure {
  const detail = viewer.isOperator ? failure.detail : '';

  return {
    message: failure.message || FALLBACK,
    detail,
    hasDetail: detail !== '',
    detailOpen: false,
    reference: failure.reference,
    referenceNote: 'Quote this reference when reporting the problem.',
    succeeded: false,
    action: failure.retryable ? 'retry' : 'report',
  };
}
