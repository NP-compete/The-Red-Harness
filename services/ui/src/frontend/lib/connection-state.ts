export type ConnectionState = 'idle' | 'streaming' | 'reconnecting' | 'failed';

export interface Connection {
  state: ConnectionState;
  attempts: number;
}

export interface PresentedConnection {
  banner?: string;
  canSend: boolean;
  keepTranscript: boolean;
  action?: 'retry';
}

const GIVE_UP_AFTER = 5;

export function presentConnection({ state, attempts }: Connection): PresentedConnection {
  if (state === 'failed') {
    return {
      banner: 'This answer did not finish. The run may have stopped.',
      canSend: true,
      keepTranscript: true,
    };
  }

  if (state === 'reconnecting') {
    const givenUp = attempts > GIVE_UP_AFTER;
    return {
      banner: givenUp
        ? 'We could not reconnect. The run may still be running — try again to pick it up.'
        : 'Reconnecting. The run is still running.',
      canSend: false,
      // The answer so far is real work; clearing it on a dropped socket
      // loses something the person was reading.
      keepTranscript: true,
      action: givenUp ? 'retry' : undefined,
    };
  }

  return { canSend: state === 'idle', keepTranscript: true };
}
