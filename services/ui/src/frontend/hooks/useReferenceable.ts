import { useTranslation } from 'react-i18next';
import { useEffect, useState } from 'react';

import { buildAgentApiUrl } from '../lib/app-paths';
import { fileSize } from '../lib/file-size';
import { saySize } from '../lib/say-size';
import type { Known, Referenceable } from '../lib/reference-palette';
import { listWorkspaceFiles } from '../services/workspace-files';
import { readLibrary } from '../services/knowledge-api';

async function specialists(): Promise<Referenceable[]> {
  try {
    const response = await fetch(buildAgentApiUrl('/subagents'), {
      credentials: 'same-origin',
    });
    if (!response.ok) return [];
    const body = (await response.json()) as {
      subagents?: Array<{ name?: string; description?: string }>;
    };
    return (body.subagents ?? [])
      .filter((one) => one.name)
      .map((one) => ({ name: one.name as string, about: one.description ?? '' }));
  } catch {
    return [];
  }
}

/**
 * The documents this person keeps, and their teams'.
 *
 * Both are already listed on the documents page, so naming
 * one here reaches nothing new. Leaving them out meant the
 * document somebody most wants to point at — the one they
 * uploaded an hour ago — was the one the shorthand could not
 * name.
 */
async function uploaded(): Promise<Referenceable[]> {
  const found = await readLibrary();
  if (!found) return [];

  const mine = (found.documents ?? []).map((document) => ({
    name: document.title || document.id,
    about: 'your documents',
  }));
  const shared = (found.team ?? []).map((document) => ({
    name: document.title || document.id,
    // Which team, because a file the agent wrote and a
    // document somebody uploaded can share a name and
    // picking the wrong one is silent.
    about: document.team ? `${document.team}'s documents` : 'shared documents',
  }));
  return [...mine, ...shared];
}


/**
 * What a person can name in a message.
 *
 * Both lists are things they can already open elsewhere, so the
 * shorthand reaches nothing new — it only saves them typing a name
 * they would otherwise have to get exactly right.
 */
export function useReferenceable(): Known {
  const { t } = useTranslation();
  const [known, setKnown] = useState<Known>({ subagents: [], documents: [] });

  useEffect(() => {
    let alive = true;
    // One list failing must not cost the other: they come from
    // different places and fail for different reasons.
    // Settled, not all: three lists from three places that
    // fail for three reasons, and one failing must not empty
    // the others.
    void Promise.allSettled([specialists(), listWorkspaceFiles(), uploaded()]).then(
      ([agents, files, mine]) => {
        if (!alive) return;
        setKnown({
          subagents: agents.status === 'fulfilled' ? agents.value : [],
          documents: [
            ...(files.status === 'fulfilled'
              ? files.value.map((file) => ({
                  name: file.path.replace(/^\//, ''),
                  about: saySize(fileSize(file.bytes), t),
                }))
              : []),
            ...(mine.status === 'fulfilled' ? mine.value : []),
          ],
        });
      },
    );
    return () => {
      alive = false;
    };
  }, []);

  return known;
}
