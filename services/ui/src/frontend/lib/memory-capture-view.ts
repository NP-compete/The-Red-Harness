export type CaptureDecision = 'keep' | 'ask' | 'discard';

export interface CaptureState {
  decision: CaptureDecision;
  text: string;
  reason: string;
}

export interface PresentedCapture {
  headline: string;
  text: string;
  detail: string;
  actions: string[];
  blocking: boolean;
}

export function presentCapture(capture: CaptureState): PresentedCapture | null {
  // Nothing was written, so there is nothing to tell anyone about.
  if (capture.decision === 'discard') {
    return null;
  }

  const asking = capture.decision === 'ask';

  return {
    headline: asking ? 'Remember this?' : 'Remembered',
    text: capture.text,
    detail: asking ? capture.reason : '',
    actions: asking ? ['Remember', 'Not this'] : ['Forget this'],
    blocking: asking,
  };
}
