import { useTranslation } from 'react-i18next';
import type { TodoItem } from '../types/deep-agent';
import { presentProgress, type Phrase } from '../lib/progress-view';
import { useQuietFor } from '../hooks/useQuietFor';

interface TodoProgressProps {
  todos: TodoItem[];
  isLoading: boolean;
}

/** Where the run has got to, in the words of its own task list. */
export function TodoProgress({ todos, isLoading }: TodoProgressProps) {
  const { t } = useTranslation();
  const elapsedSeconds = useQuietFor(isLoading, 'run');

  if (todos.length === 0) {
    return null;
  }

  const done = todos.filter((todo) => todo.status === 'completed').length;
  const current = todos.find((todo) => todo.status === 'in_progress');

  const progress = presentProgress({
    doing: isLoading ? (current?.content ?? '') : '',
    done,
    total: todos.length,
    // A fraction of a list the agent is still adding to would move
    // backwards, so the bar is left out rather than made up.
    fraction: null,
    // Never measured: the agent does not estimate how long it has left.
    remainingSeconds: null,
    elapsedSeconds,
    totalIsFinal: !isLoading,
    overrunning: false,
  });

  const say = (phrase: Phrase) =>
    t(phrase.key, { count: phrase.count, ...(phrase.values ?? {}) });

  return (
    <span className="text-[11px] text-muted-foreground">
      {progress.finished ? t('progress.finished') : progress.doing} · {say(progress.steps)} ·{' '}
      {say(progress.elapsed)}
    </span>
  );
}
