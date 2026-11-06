import { describe, expect, it } from 'vitest';

import { idsToDelete } from './bulk-delete';

describe('idsToDelete', () => {
  it('takes exactly what was picked', async () => {
    const got = await idsToDelete({
      beyondThisPage: false,
      pickedOnPage: () => ['t1', 't3'],
      targets: () => [],
      listAll: async () => ['t1', 't2', 't3'],
    });
    expect(got).toEqual(['t1', 't3']);
  });

  it('never asks the server for a list it does not need', async () => {
    let asked = false;
    await idsToDelete({
      beyondThisPage: false,
      pickedOnPage: () => ['t1'],
      targets: () => [],
      listAll: async () => {
        asked = true;
        return [];
      },
    });
    expect(asked).toBe(false);
  });

  it('reaches every conversation under a select-all', async () => {
    const got = await idsToDelete({
      beyondThisPage: true,
      pickedOnPage: () => ['t1', 't2'],
      targets: (all) => all,
      listAll: async () => ['t1', 't2', 't40'],
    });
    expect(got).toEqual(['t1', 't2', 't40']);
  });

  it('respects a row dropped from a select-all', async () => {
    const got = await idsToDelete({
      beyondThisPage: true,
      pickedOnPage: () => ['t1'],
      targets: (all) => all.filter((id) => id !== 't2'),
      listAll: async () => ['t1', 't2', 't40'],
    });
    expect(got).toEqual(['t1', 't40']);
  });

  it('falls back to the visible rows when the full list cannot be had', async () => {
    // Deleting nothing would read as the button being broken; deleting
    // what is on screen is what the reader can see they asked for.
    const got = await idsToDelete({
      beyondThisPage: true,
      pickedOnPage: () => ['t1', 't2'],
      targets: (all) => all,
      listAll: async () => null,
    });
    expect(got).toEqual(['t1', 't2']);
  });
});
