import { UserCheck } from 'lucide-react';

import {
  presentAnnotationQueue,
  type AnnotationEntry,
} from '../../../lib/annotation-queue-view';

/** The graded turns of a run that a person should look at. */
export function ReviewQueueCard({ review }: { review?: AnnotationEntry[] }) {
  if (!review || review.length === 0) {
    return null;
  }

  const queue = presentAnnotationQueue(review);

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <UserCheck className="h-4 w-4 text-primary/70" />
        <h3 className="text-sm font-semibold text-foreground">{queue.headline}</h3>
      </div>
      <ul className="space-y-1.5">
        {queue.rows.map((row) => (
          <li key={row.item} className="flex items-baseline gap-2 text-xs">
            <span className="font-mono text-foreground">{row.item}</span>
            <span className="text-muted-foreground">{row.why}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
