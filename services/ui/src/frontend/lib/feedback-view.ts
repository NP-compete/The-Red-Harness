export interface FeedbackState {
  runId: string;
  rating: 'up' | 'down' | null;
  comment: string;
  submitted: boolean;
  shareTranscript: boolean;
  containsSensitiveData: boolean;
}

export interface PresentedFeedback {
  prompt: string;
  commentPrompt: string;
  shareOption: string;
  sharing: boolean;
  warning: string;
  showComment: boolean;
  canSubmit: boolean;
}

export function presentFeedback(state: FeedbackState): PresentedFeedback {
  const rated = state.rating !== null;

  return {
    prompt: state.submitted ? 'Thanks' : 'Was this useful?',
    commentPrompt:
      state.rating === 'down' ? 'What went wrong? (optional)' : 'What worked well? (optional)',
    shareOption: 'Include this conversation so it can be looked at',
    sharing: state.shareTranscript,
    // Only a warning when the data would actually leave.
    warning:
      state.shareTranscript && state.containsSensitiveData
        ? 'This conversation contains sensitive data that would be shared'
        : '',
    showComment: rated && !state.submitted,
    canSubmit: rated && !state.submitted,
  };
}
