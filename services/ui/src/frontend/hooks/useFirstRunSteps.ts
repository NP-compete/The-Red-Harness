import { useEffect, useState } from 'react';

import type { FirstRunStep } from '../lib/first-run-view';
import { listDocuments } from '../services/documents-api';

/**
 * What a new workspace still has to do, worked out from what it has.
 *
 * Only steps this deployment can actually see are offered. Inviting
 * a team is not among them: there is no team data here, so the card
 * would lead nowhere. A step that cannot be checked is not offered
 * either — guessing "no documents" when the call fails would greet
 * an established workspace as though it were empty.
 */
export function useFirstRunSteps({ chats }: { chats: number }): FirstRunStep[] {
  const [documents, setDocuments] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    void listDocuments()
      .then((found) => {
        if (alive) setDocuments(found.documents?.length ?? 0);
      })
      .catch(() => {
        // Unknown, which is not the same as none.
      });
    return () => {
      alive = false;
    };
  }, []);

  if (documents === null) return [];

  const outstanding: FirstRunStep[] = [];
  // Connecting comes first: the first question is better answered
  // once there is something of your own to answer it from.
  if (documents === 0) outstanding.push('connect_source');
  if (chats === 0) outstanding.push('ask_something');
  return outstanding;
}
