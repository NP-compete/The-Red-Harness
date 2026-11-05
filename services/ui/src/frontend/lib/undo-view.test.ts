import { describe, expect, it } from 'vitest';

import { presentUndo } from '@/lib/undo-view';

const plan = {
  steps: [
    { target: 'out/b.md', kind: 'file-written' },
    { target: 'out/a.md', kind: 'file-written' },
  ],
  cannotUndo: ['email-sent: ana'],
  complete: false,
  result: null,
};

describe('presentUndo', () => {
  it('says how much will be put back', () => {
    expect(presentUndo(plan).headline).toBe('Undo 2 changes');
  });

  it('uses the singular for one change', () => {
    const one = { ...plan, steps: [plan.steps[0]] };
    expect(presentUndo(one).headline).toBe('Undo 1 change');
  });

  it('lists what will be put back, newest first', () => {
    expect(presentUndo(plan).steps).toEqual(['out/b.md', 'out/a.md']);
  });

  it('says plainly what will be left behind', () => {
    expect(presentUndo(plan).leftBehind).toEqual(['email-sent: ana']);
  });

  it('warns that the undo is partial', () => {
    expect(presentUndo(plan).warning).toBe('1 change cannot be undone and will stay');
  });

  it('has no warning when everything can be undone', () => {
    const clean = { ...plan, cannotUndo: [], complete: true };
    expect(presentUndo(clean).warning).toBe('');
  });

  it('asks for confirmation before undoing', () => {
    expect(presentUndo(plan).confirmFirst).toBe(true);
  });

  it('can be run when there is something to undo', () => {
    expect(presentUndo(plan).canRun).toBe(true);
  });

  it('cannot be run when nothing is reversible', () => {
    const stuck = { ...plan, steps: [], complete: false };
    expect(presentUndo(stuck).canRun).toBe(false);
  });

  it('says plainly when nothing can be put back', () => {
    const stuck = { ...plan, steps: [], complete: false };
    expect(presentUndo(stuck).headline).toBe('Nothing here can be undone');
  });

  it('reports a finished undo plainly', () => {
    const done = {
      ...plan,
      result: { allUndone: true, failed: [], message: '2 undone', warning: '' },
    };
    expect(presentUndo(done).headline).toBe('2 undone');
  });

  it('does not call a partial undo a success', () => {
    const partial = {
      ...plan,
      result: {
        allUndone: false,
        failed: ['out/a.md'],
        message: '1 undone, 1 could not be undone',
        warning: 'this was partly undone, so things are not as they were',
      },
    };
    expect(presentUndo(partial).succeeded).toBe(false);
  });

  it('names what failed so it can be dealt with by hand', () => {
    const partial = {
      ...plan,
      result: {
        allUndone: false,
        failed: ['out/a.md'],
        message: '1 undone, 1 could not be undone',
        warning: 'x',
      },
    };
    expect(presentUndo(partial).leftBehind).toEqual(['out/a.md']);
  });

  it('treats a partial undo as serious', () => {
    const partial = {
      ...plan,
      result: { allUndone: false, failed: ['a'], message: 'x', warning: 'y' },
    };
    expect(presentUndo(partial).severity).toBe('high');
  });
});
