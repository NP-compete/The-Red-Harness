export interface RecoveredDraft {
  outcome: 'offered' | 'already-sent' | 'nothing-to-recover' | 'too-old' | 'thread-gone';
  text: string;
  attachments: string[];
  ageSeconds: number;
  reason: string;
}

export interface PresentedDraft {
  headline: string;
  detail: string;
  preview: string;
  attachmentNote: string;
  autoDiscards: false;
  action: 'restore' | 'copy';
  secondaryAction: 'discard';
}

const PREVIEW_LENGTH = 80;

export function presentDraft(draft: RecoveredDraft): PresentedDraft | null {
  if (draft.outcome !== 'offered' && draft.outcome !== 'thread-gone') return null;

  const orphaned = draft.outcome === 'thread-gone';
  const files = draft.attachments.length;

  return {
    headline: orphaned
      ? 'An unsent message survived a deleted conversation'
      : 'You have an unsent message here',
    detail: draft.reason,
    preview: shorten(draft.text),
    attachmentNote:
      files > 0 ? `${files} attachment${files === 1 ? ' was' : 's were'} waiting with it` : '',
    // Unsent words are never thrown away on the reader's behalf.
    autoDiscards: false,
    // There is nowhere to restore an orphan to, but it can still be kept.
    action: orphaned ? 'copy' : 'restore',
    secondaryAction: 'discard',
  };
}

function shorten(text: string): string {
  return text.length <= PREVIEW_LENGTH ? text : `${text.slice(0, PREVIEW_LENGTH)}…`;
}
