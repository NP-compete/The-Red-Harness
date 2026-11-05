import { describe, expect, it } from 'vitest';

import { presentAccess } from '@/lib/thread-access-view';

const write = { level: 'write' as const, reason: '', viaLink: false, heldBy: '' };

describe('presentAccess', () => {
  it('shows nothing when the viewer has full access', () => {
    expect(presentAccess(write)).toBeNull();
  });

  it('says plainly when the conversation is read only', () => {
    const readonly = { ...write, level: 'read' as const };
    expect(presentAccess(readonly)?.headline).toBe('You can read this but not change it');
  });

  it('says who is working in it', () => {
    const busy = { ...write, level: 'read' as const, heldBy: 'bo', reason: 'bo is working in this now' };
    expect(presentAccess(busy)?.detail).toBe('bo is working in this now');
  });

  it('offers to take over once the other person is done', () => {
    const busy = { ...write, level: 'read' as const, heldBy: 'bo', reason: 'x' };
    expect(presentAccess(busy)?.action).toBe('ask-to-edit');
  });

  it('says plainly when access came from a link', () => {
    const guest = { ...write, level: 'read' as const, viaLink: true };
    expect(presentAccess(guest)?.headline).toBe('You are viewing this through a shared link');
  });

  it('explains that a link cannot grant editing', () => {
    const guest = { ...write, level: 'read' as const, viaLink: true };
    expect(presentAccess(guest)?.detail).toBe('A shared link only ever allows reading');
  });

  it('offers nothing to request when viewing through a link', () => {
    const guest = { ...write, level: 'read' as const, viaLink: true };
    expect(presentAccess(guest)?.action).toBe('none');
  });

  it('says plainly when there is no access at all', () => {
    const denied = {
      ...write,
      level: 'none' as const,
      reason: 'this conversation is not shared with you',
    };
    expect(presentAccess(denied)?.headline).toBe('You cannot open this conversation');
  });

  it('offers to ask for access when there is none', () => {
    const denied = { ...write, level: 'none' as const, reason: 'x' };
    expect(presentAccess(denied)?.action).toBe('request-access');
  });

  it('treats no access as the most serious', () => {
    const denied = { ...write, level: 'none' as const, reason: 'x' };
    expect(presentAccess(denied)?.severity).toBe('high');
  });

  it('treats read only as routine', () => {
    expect(presentAccess({ ...write, level: 'read' as const })?.severity).toBe('info');
  });

  it('does not let the editor be used without write access', () => {
    expect(presentAccess({ ...write, level: 'read' as const })?.canEdit).toBe(false);
  });

  it('hides the conversation entirely when there is no access', () => {
    const denied = { ...write, level: 'none' as const, reason: 'x' };
    expect(presentAccess(denied)?.canRead).toBe(false);
  });

  it('allows reading when read access was granted', () => {
    expect(presentAccess({ ...write, level: 'read' as const })?.canRead).toBe(true);
  });
});
