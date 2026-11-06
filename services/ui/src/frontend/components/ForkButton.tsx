import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { forkLabel } from '../lib/feedback-labels';
import { GitBranch } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { forkThread } from '../services/fork-api';
import { useAppDispatch } from '../redux/hooks';
import { addChat } from '../redux/slices/chats';

interface ForkButtonProps {
  chatId: string;
  /**
   * How many messages to keep — the index of this message in the thread
   * plus one. Forking "at" a message means keeping it.
   */
  messageIndex: number;
  onForked?: (threadId: string) => void;
}

/**
 * Branch the conversation from this point into a new thread.
 *
 * The original is left alone, so this is a safe thing to click: nothing
 * about the conversation you are reading changes.
 */
export function ForkButton({ chatId, messageIndex, onForked }: ForkButtonProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  // Asked twice. This icon sits in a row of 6x6 icons beside the
  // rating buttons, and forking carries you out of the conversation
  // you were reading — a stray click should not move you.
  const [asking, setAsking] = useState(false);

  const handleFork = async () => {
    if (busy) return;
    if (!asking) {
      setAsking(true);
      return;
    }
    setAsking(false);
    setBusy(true);
    setFailed(false);
    try {
      const { thread_id } = await forkThread(chatId, messageIndex);

      // Register the fork before navigating. The server created the
      // thread, but the sidebar is driven by the store — navigating
      // straight to an id it has never seen lands on an empty page
      // with no entry in the list, which reads as the button having
      // done nothing. The messages themselves are loaded from the
      // server by the chat page.
      dispatch(
        addChat({
          id: thread_id,
          title: 'Forked conversation',
          timestamp: new Date().toISOString(),
          preview: 'Branched from an earlier message',
          messages: [],
          historicalActivities: {},
          feedback: {},
        }),
      );

      onForked?.(thread_id);
      navigate(`/chat/${thread_id}`);
    } catch {
      // Nothing was created on a failure — the server deletes a fork it
      // could not seed — so retrying is safe.
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleFork}
      onBlur={() => setAsking(false)}
      onKeyDown={(event) => {
        if (event.key === 'Escape') setAsking(false);
      }}
      disabled={busy}
      title={
        asking
          ? t('rating.forkConfirm')
          : failed
            ? t('rating.forkFailedTitle')
            : t('rating.forkTitle')
      }
      aria-label={t(forkLabel({ busy, failed, asking }))}
      className={`inline-flex items-center justify-center h-6 rounded text-muted-foreground hover:text-foreground hover:bg-secondary/60 disabled:opacity-50 transition-colors ${
        // Asking needs words, and words are wider than an icon. Growing
        // the button beats wrapping three lines inside a 24px square,
        // and keeps any translation on one line.
        asking ? 'w-auto px-1.5 whitespace-nowrap' : 'w-6'
      }`}
    >
      {asking ? (
        <span className="text-[10px] leading-none text-foreground">
          {t('rating.forkConfirmShort')}
        </span>
      ) : (
        <GitBranch
          className={`w-3.5 h-3.5 ${failed ? 'text-destructive' : ''}`}
          aria-hidden="true"
        />
      )}
    </button>
  );
}
