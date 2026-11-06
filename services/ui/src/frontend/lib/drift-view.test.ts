import { describe, expect, it } from 'vitest';

import { presentDrift } from '@/lib/drift-view';

const steady = { movement: 'steady' as const, gap: 0.0, outliers: [] as string[] };

describe('presentDrift', () => {
  it('says scores are holding', () => {
    expect(presentDrift(steady).headline).toBe('Scores are holding steady');
  });

  it('says plainly when scores are falling', () => {
    const falling = { ...steady, movement: 'falling' as const, gap: -0.12 };
    expect(presentDrift(falling).headline).toBe('Scores are falling');
  });

  it('says how far below the baseline things sit', () => {
    const falling = { ...steady, movement: 'falling' as const, gap: -0.12 };
    expect(presentDrift(falling).detail).toBe('12 points below baseline');
  });

  it('says how far above the baseline a rise has got', () => {
    const rising = { ...steady, movement: 'rising' as const, gap: 0.08 };
    expect(presentDrift(rising).detail).toBe('8 points above baseline');
  });

  it('says nothing about a gap worth nothing', () => {
    expect(presentDrift(steady).detail).toBe('At baseline');
  });

  it('admits when there is not enough history to say', () => {
    const unknown = { ...steady, movement: 'unknown' as const };
    expect(presentDrift(unknown).headline).toBe('Not enough runs to tell');
  });

  it('gives no detail it cannot stand behind', () => {
    const unknown = { ...steady, movement: 'unknown' as const };
    expect(presentDrift(unknown).detail).toBe('');
  });

  it('names runs that sat apart from the rest', () => {
    const wobbly = { ...steady, outliers: ['r2'] };
    expect(presentDrift(wobbly).outlierNote).toBe('1 run sat well outside the rest: r2');
  });

  it('names several such runs', () => {
    const wobbly = { ...steady, outliers: ['r2', 'r5'] };
    expect(presentDrift(wobbly).outlierNote).toBe('2 runs sat well outside the rest: r2, r5');
  });

  it('adds no note when every run was in line', () => {
    expect(presentDrift(steady).outlierNote).toBe('');
  });

  it('treats a fall as worth someone looking', () => {
    const falling = { ...steady, movement: 'falling' as const, gap: -0.12 };
    expect(presentDrift(falling).severity).toBe('high');
  });

  it('treats a rise as nothing to act on', () => {
    const rising = { ...steady, movement: 'rising' as const, gap: 0.08 };
    expect(presentDrift(rising).severity).toBe('info');
  });

  it('treats missing history as something to note, not to worry about', () => {
    const unknown = { ...steady, movement: 'unknown' as const };
    expect(presentDrift(unknown).severity).toBe('info');
  });
});
