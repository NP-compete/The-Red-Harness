import { describe, expect, it } from 'vitest';

import { presentEntitlement } from '@/lib/entitlement-view';

const entitlement = {
  team: 'finance',
  agents: ['reporter', 'reconciler'],
  seats: 5,
  seatsTaken: ['ana', 'bo'],
  viewerId: 'ana',
  adminIds: ['cy'],
};

describe('presentEntitlement', () => {
  it('says how many seats are left', () => {
    expect(presentEntitlement(entitlement).seats).toBe('3 of 5 seats free');
  });

  it('says when the last seat is gone', () => {
    const full = { ...entitlement, seatsTaken: ['ana', 'bo', 'cy', 'dee', 'eli'] };
    expect(presentEntitlement(full).seats).toBe('No seats free');
  });

  it('warns when only one seat is left', () => {
    const nearly = { ...entitlement, seatsTaken: ['ana', 'bo', 'cy', 'dee'] };
    expect(presentEntitlement(nearly).seatsLow).toBe(true);
  });

  it('does not warn when there is room', () => {
    expect(presentEntitlement(entitlement).seatsLow).toBe(false);
  });

  it('says the viewer holds a seat', () => {
    expect(presentEntitlement(entitlement).viewerHasSeat).toBe(true);
  });

  it('says the viewer holds no seat', () => {
    expect(presentEntitlement({ ...entitlement, viewerId: 'dee' }).viewerHasSeat).toBe(false);
  });

  it('lists the agents the team may use', () => {
    expect(presentEntitlement(entitlement).agents).toEqual(['reporter', 'reconciler']);
  });

  it('says plainly when the team may use nothing', () => {
    const none = { ...entitlement, agents: [] };
    expect(presentEntitlement(none).note).toBe('This team has no agents licensed yet');
  });

  it('tells someone without a seat who to ask', () => {
    const shown = presentEntitlement({ ...entitlement, viewerId: 'dee' });
    expect(shown.note).toBe('Ask cy for a seat');
  });

  it('names several administrators when there are several', () => {
    const shown = presentEntitlement({
      ...entitlement,
      viewerId: 'dee',
      adminIds: ['cy', 'eli'],
    });
    expect(shown.note).toBe('Ask cy or eli for a seat');
  });

  it('does not pretend there is someone to ask when there is nobody', () => {
    const shown = presentEntitlement({ ...entitlement, viewerId: 'dee', adminIds: [] });
    expect(shown.note).toBe('No administrator is set for this team');
  });

  it('has nothing to add for someone who already has a seat', () => {
    expect(presentEntitlement(entitlement).note).toBe('');
  });

  it('offers a seat request to someone without one', () => {
    expect(presentEntitlement({ ...entitlement, viewerId: 'dee' }).action).toBe('request-seat');
  });

  it('offers nothing to someone who already has a seat', () => {
    expect(presentEntitlement(entitlement).action).toBe('none');
  });

  it('offers nothing when there are no seats to give', () => {
    const full = {
      ...entitlement,
      viewerId: 'dee',
      seatsTaken: ['ana', 'bo', 'cy', 'eli', 'fay'],
    };
    expect(presentEntitlement(full).action).toBe('none');
  });
});
