import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * A conversation can be put behind a link from the conversation.
 *
 * Settings lists the links somebody has made and lets them be
 * revoked. Nothing anywhere could make one: the only caller of
 * `createShare` was a control mounted nowhere, so the settings
 * page managed a set that could never have anything in it.
 *
 * The control belongs with export, in the thread's own corner —
 * both answer "get this conversation to somebody else", and a
 * person who wants that looks in one place.
 */

const transcript = () =>
  readFileSync(join(__dirname, '..', 'ChatMessagesView.tsx'), 'utf-8');

describe('the control is reachable', () => {
  it('is in the transcript', () => {
    expect(transcript()).toContain('ShareControl');
  });

  it('sits with export, not somewhere of its own', () => {
    const source = transcript();
    const corner = source.slice(
      source.indexOf('absolute top-2 right-3'),
      source.indexOf('</DropdownList>'),
    );
    expect(corner).toContain('ShareControl');
  });

  it('is given the conversation it would share', () => {
    const source = transcript();
    const at = source.indexOf('<ShareControl');
    expect(source.slice(at, at + 120)).toMatch(/threadId=\{/);
  });
});

describe('what settings could do before', () => {
  it('still only lists and revokes', () => {
    // The division is deliberate: making a link is an act on
    // one conversation, and the settings page is about all of
    // them. Moving creation there would ask somebody to pick a
    // conversation from a list to share the one they are in.
    const settings = readFileSync(
      join(__dirname, '..', 'settings', 'SharedLinks.tsx'),
      'utf-8',
    );
    expect(settings).toContain('listShares');
    expect(settings).toContain('revokeShare');
    expect(settings).not.toContain('createShare');
  });
});
