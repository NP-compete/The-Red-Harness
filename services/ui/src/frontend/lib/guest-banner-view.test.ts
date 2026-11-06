import { describe, expect, it } from 'vitest';

import { presentGuestBanner } from '@/lib/guest-banner-view';

const guest = {
  isGuest: true,
  mayWrite: true,
  daysLeft: 7,
  expired: false,
  organisation: 'Northwind',
};

describe('presentGuestBanner', () => {
  it('shows nothing to someone who belongs here', () => {
    expect(presentGuestBanner({ ...guest, isGuest: false })).toBeNull();
  });

  it('tells a guest whose conversation they are in', () => {
    expect(presentGuestBanner(guest)?.headline).toBe("You are a guest in Northwind's workspace");
  });

  it('says what a guest can see', () => {
    expect(presentGuestBanner(guest)?.detail).toBe('You can see this conversation and nothing else');
  });

  it('says when a read-only guest cannot reply', () => {
    const quiet = { ...guest, mayWrite: false };
    expect(presentGuestBanner(quiet)?.detail).toBe(
      'You can read this conversation and nothing else',
    );
  });

  it('says how long the invitation has left', () => {
    expect(presentGuestBanner(guest)?.expiry).toBe('Your access ends in 7 days');
  });

  it('counts a final day in the singular', () => {
    expect(presentGuestBanner({ ...guest, daysLeft: 1 })?.expiry).toBe('Your access ends in 1 day');
  });

  it('says plainly when access ends today', () => {
    expect(presentGuestBanner({ ...guest, daysLeft: 0 })?.expiry).toBe('Your access ends today');
  });

  it('says plainly when access has already ended', () => {
    const over = { ...guest, daysLeft: 0, expired: true };
    expect(presentGuestBanner(over)?.expiry).toBe('Your access has ended');
  });

  it('treats an expiry still days away as a quiet note', () => {
    expect(presentGuestBanner(guest)?.severity).toBe('info');
  });

  it('treats an expiry about to land as worth noticing', () => {
    expect(presentGuestBanner({ ...guest, daysLeft: 1 })?.severity).toBe('medium');
  });

  it('treats an ended invitation as the end of the road', () => {
    const over = { ...guest, daysLeft: 0, expired: true };
    expect(presentGuestBanner(over)?.severity).toBe('high');
  });

  it('cannot be dismissed, since it is the whole context', () => {
    expect(presentGuestBanner(guest)?.dismissible).toBe(false);
  });
});
