import { useState } from 'react';
import { Alert, AlertActionLink } from '@patternfly/react-core';

import { presentDraft } from '../lib/draft-recovery-view';
import { draftStorage } from '../services/draftStorage';

interface DraftNoticeProps {
  threadId: string;
  onRestore: (text: string) => void;
}

/** An unsent message waiting in a conversation the reader came back to. */
export function DraftNotice({ threadId, onRestore }: DraftNoticeProps) {
  const [draft, setDraft] = useState(() => draftStorage.load(threadId));

  if (!draft) {
    return null;
  }

  const presented = presentDraft({
    outcome: 'offered',
    text: draft.text,
    attachments: [],
    ageSeconds: draft.ageSeconds,
    reason: '',
  });

  if (!presented) {
    return null;
  }

  return (
    <Alert
      variant="info"
      isInline
      title={presented.headline}
      role="status"
      actionLinks={
        <span className="flex gap-3">
          <AlertActionLink
            onClick={() => {
              onRestore(draft.text);
              draftStorage.discard(threadId);
              setDraft(null);
            }}
          >
            Restore
          </AlertActionLink>
          {/* Unsent words are never thrown away on the reader's behalf. */}
          <AlertActionLink
            onClick={() => {
              draftStorage.discard(threadId);
              setDraft(null);
            }}
          >
            Discard
          </AlertActionLink>
        </span>
      }
    >
      {presented.preview}
    </Alert>
  );
}
