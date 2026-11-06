import { AlertCircle, RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { presentFailure } from '../lib/failure-view';

interface FailureNoticeProps {
  error: string | null;
  onRetry: () => void;
}

/** What went wrong, in terms the reader can act on. */
export function FailureNotice({ error, onRetry }: FailureNoticeProps) {
  const { t } = useTranslation();

  if (!error) {
    return null;
  }

  const failure = presentFailure(
    {
      // Translated like the rest of the transcript. The agent's own
      // words are plumbing and carry no promise of reading as a
      // sentence, so the detail carries them instead.
      message: t('chat.agentError'),
      detail: error,
      reference: '',
      retryable: true,
    },
    // Shown to everyone, not just operators: the agent's error text is
    // the only account the reader gets of what went wrong, and hiding
    // it leaves a heading with nothing under it. It is the app's own
    // message, not a stack trace.
    { isOperator: true },
  );

  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-2xl border border-border bg-card px-4 py-3 shadow-card"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-destructive" />
      <div>
        <p className="text-sm text-foreground">{failure.message}</p>
        {failure.hasDetail && (
          <p className="mt-1 break-words rounded-md bg-destructive/5 px-2 py-1.5 font-mono text-xs text-destructive">
            {failure.detail}
          </p>
        )}
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <RotateCcw className="h-3 w-3" />
          {t('chat.retry')}
        </button>
      </div>
    </div>
  );
}
