export type Handling =
  | 'folded-in'
  | 'redirected'
  | 'stopped'
  | 'answered'
  | 'ignored'
  | 'too-late';

export interface InterruptionResult {
  handling: Handling;
  continues: boolean;
  keepsWork: boolean;
  appliesAfterCurrentStep: boolean;
  reason: string;
  tool: string;
}

export interface PresentedInterruption {
  message: string;
  pending: string;
  losesWork: boolean;
  interruptsReading: boolean;
}

export function presentInterruption(result: InterruptionResult): PresentedInterruption {
  return {
    message: message(result),
    // Promising an immediate stop while a write is in flight would be a lie.
    pending: result.appliesAfterCurrentStep
      ? `Waiting for ${result.tool} to finish first`
      : '',
    losesWork: !result.keepsWork,
    interruptsReading: result.handling === 'stopped' || result.handling === 'redirected',
  };
}

function message(result: InterruptionResult): string {
  switch (result.handling) {
    case 'folded-in':
      return 'Added to what I am working on';
    case 'redirected':
      return `Starting again: ${result.reason}`;
    case 'stopped':
      return `Stopped: ${result.reason}`;
    case 'answered':
      return 'Still working — here is where I am';
    case 'too-late':
      return 'This run had already finished';
    default:
      return '';
  }
}
