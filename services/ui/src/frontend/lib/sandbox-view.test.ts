import { describe, expect, it } from 'vitest';

import { presentSandbox } from '@/lib/sandbox-view';

const plan = {
  permitted: true,
  seconds: 30,
  memoryMb: 512,
  network: false,
  writablePaths: ['/tmp/work'],
  maxOutputBytes: 100_000,
  reason: '',
};

describe('presentSandbox', () => {
  it('says how long the code may run', () => {
    expect(presentSandbox(plan).limits).toContain('up to 30 seconds');
  });

  it('says how much memory it may use', () => {
    expect(presentSandbox(plan).limits).toContain('512 MB of memory');
  });

  it('says plainly that it cannot reach the network', () => {
    expect(presentSandbox(plan).network).toBe('no network access');
  });

  it('says plainly when it can reach the network', () => {
    expect(presentSandbox({ ...plan, network: true }).network).toBe('can reach the network');
  });

  it('treats network access as the thing to look at', () => {
    expect(presentSandbox({ ...plan, network: true }).severity).toBe('high');
  });

  it('treats an offline run as routine', () => {
    expect(presentSandbox(plan).severity).toBe('low');
  });

  it('lists what it may write to', () => {
    expect(presentSandbox(plan).writable).toEqual(['/tmp/work']);
  });

  it('says plainly when it may write nowhere', () => {
    expect(presentSandbox({ ...plan, writablePaths: [] }).writableNote).toBe(
      'cannot write any files',
    );
  });

  it('says what it may write when it can', () => {
    expect(presentSandbox(plan).writableNote).toBe('can write to 1 place');
  });

  it('counts several writable places', () => {
    const wider = { ...plan, writablePaths: ['/tmp/work', '/tmp/out'] };
    expect(presentSandbox(wider).writableNote).toBe('can write to 2 places');
  });

  it('treats writable paths plus network as the most serious combination', () => {
    const open = { ...plan, network: true, writablePaths: ['/tmp/work'] };
    expect(presentSandbox(open).warning).toBe(
      'This code can both read your files and send data out',
    );
  });

  it('has no such warning without network access', () => {
    expect(presentSandbox(plan).warning).toBe('');
  });

  it('shows a refused plan as refused rather than as limits', () => {
    const refused = { ...plan, permitted: false, reason: 'there is nothing to run' };
    expect(presentSandbox(refused).limits).toBe('there is nothing to run');
  });

  it('does not offer to run a refused plan', () => {
    const refused = { ...plan, permitted: false, reason: 'there is nothing to run' };
    expect(presentSandbox(refused).canRun).toBe(false);
  });

  it('offers to run a permitted plan', () => {
    expect(presentSandbox(plan).canRun).toBe(true);
  });
});
