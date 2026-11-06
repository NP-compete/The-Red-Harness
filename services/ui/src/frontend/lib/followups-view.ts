export interface OfferedFollowup {
  text: string;
  because: string;
}

export interface FollowupsState {
  offered: OfferedFollowup[];
  setAside: number;
  reason: string;
}

export interface FollowupChip {
  text: string;
  sends: string;
  because: string;
  guaranteed: false;
}

export interface PresentedFollowups {
  prompt: string;
  chips: FollowupChip[];
  dismissible: true;
  takesFocus: false;
}

const CHIP_LENGTH = 60;

export function presentFollowups(state: FollowupsState): PresentedFollowups | null {
  if (state.offered.length === 0) return null;

  return {
    // "Could", not "should": these are guesses about what helps next.
    prompt: 'You could ask next',
    chips: state.offered.map((followup) => ({
      text: shorten(followup.text),
      // The whole question is sent, not the shortened label.
      sends: followup.text,
      because: `about ${followup.because}`,
      guaranteed: false,
    })),
    dismissible: true,
    // The message box keeps the cursor; suggestions are an offer, not a detour.
    takesFocus: false,
  };
}

function shorten(text: string): string {
  return text.length <= CHIP_LENGTH ? text : `${text.slice(0, CHIP_LENGTH)}…`;
}
