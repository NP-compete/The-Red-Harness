import { Children, Fragment, type ReactNode } from 'react';

import { highlightClaims, type HighlightableClaim } from '../lib/claim-highlight';

const REASON: Record<string, string> = {
  unsupported: 'Not backed by what was read',
  contradicted: 'Contradicted by what was read',
};

/**
 * Mark the sentences of an answer that nothing read backs up.
 *
 * Only trouble is marked. Highlighting the sound sentences too would
 * colour the whole answer and leave the reader to find the difference.
 */
export function ClaimMarked({
  claims,
  children,
}: {
  claims: HighlightableClaim[];
  children?: ReactNode;
}) {
  const flagged = claims.filter((claim) => !claim.supported);
  if (flagged.length === 0) {
    return <>{children}</>;
  }

  return (
    <>
      {Children.map(children, (child, childIndex) => {
        // Bold, links and code keep their own elements; only the plain
        // runs between them are searched for flagged sentences.
        if (typeof child !== 'string') {
          return child;
        }
        return highlightClaims(child, flagged).map((segment, index) =>
          segment.status === 'plain' ? (
            <Fragment key={`${childIndex}-${index}`}>{segment.text}</Fragment>
          ) : (
            <mark
              key={`${childIndex}-${index}`}
              aria-description={REASON[segment.status]}
              className="bg-amber-500/15 text-inherit decoration-amber-500/60 underline decoration-wavy underline-offset-4"
            >
              {segment.text}
            </mark>
          ),
        );
      })}
    </>
  );
}
