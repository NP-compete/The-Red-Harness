import { StopCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { presentStopControl, type RunStage } from '../lib/cancel-view';

interface StopButtonProps {
  stage: RunStage;
  tool?: string;
  reversible?: boolean;
  isOwner?: boolean;
  isOperator?: boolean;
  onStop: () => void;
}

/** Stop the run in flight, promising only what stopping will actually do. */
export function StopButton({
  stage,
  tool = '',
  reversible = true,
  isOwner = true,
  isOperator = false,
  onStop,
}: StopButtonProps) {
  const { t } = useTranslation();
  const control = presentStopControl({ stage, tool, reversible, isOwner, isOperator });

  // The promise is translated like the rest of the composer; the
  // presenter decides which promise is honest to make.
  const label =
    control.label === 'Stop' ? t('input.cancelStreaming') : t('input.stopAfterStep');

  if (stage === 'done') {
    return null;
  }

  const explanation = control.blockedReason || control.confirm;

  return (
    <button
      type="button"
      className="flex items-center justify-center gap-1.5 h-8 px-2.5 rounded-full bg-destructive/10 text-destructive hover:bg-destructive/20 transition-colors disabled:opacity-40 disabled:pointer-events-none"
      onClick={onStop}
      disabled={!control.enabled}
      aria-label={label}
      title={explanation || undefined}
    >
      <StopCircle className="h-4 w-4" />
      {control.label !== 'Stop' && <span className="text-xs">{label}</span>}
    </button>
  );
}
