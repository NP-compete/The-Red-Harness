export type FeedbackAction = 'thank' | 'ask_why' | 'file' | 'route_to_policy';

export interface TriagedFeedback {
  run: string;
  action: FeedbackAction;
  comment: string;
  askedForDetail: boolean;
  attachContent: boolean;
  becomesEvalCase: boolean;
}

export interface PresentedFeedbackOutcome {
  message: string;
  prompt: string;
  choices: string[];
  detail: string;
  awaitingReply: boolean;
}

const REASONS = ['Wrong answer', 'Missed something', 'Too slow', 'Something else'];

const MESSAGE: Record<FeedbackAction, string> = {
  thank: 'Thanks',
  ask_why: '',
  file: 'Recorded — thanks for the detail',
  route_to_policy: 'Passed to whoever sets the rules for this workspace',
};

export function presentFeedbackOutcome(feedback: TriagedFeedback): PresentedFeedbackOutcome {
  const asking = feedback.action === 'ask_why';
  const sent = feedback.action === 'file' || feedback.action === 'route_to_policy';

  return {
    message: MESSAGE[feedback.action],
    prompt: asking ? 'What went wrong?' : '',
    choices: asking ? REASONS : [],
    // Whether the conversation travels with the report is the person's business.
    detail: sent
      ? feedback.attachContent
        ? 'This conversation is attached'
        : 'Only the rating is sent, not the conversation'
      : '',
    awaitingReply: asking,
  };
}
