import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useThreadSelection } from './useThreadSelection';

const page = ['t1', 't2', 't3'];

describe('useThreadSelection', () => {
  it('starts with nothing picked', () => {
    const { result } = renderHook(() => useThreadSelection(page, 3));
    expect(result.current.summary).toBe('Nothing selected');
  });

  it('picks one', () => {
    const { result } = renderHook(() => useThreadSelection(page, 3));
    act(() => result.current.toggle('t1'));
    expect(result.current.summary).toBe('1 selected');
  });

  it('knows which one is picked', () => {
    const { result } = renderHook(() => useThreadSelection(page, 3));
    act(() => result.current.toggle('t1'));
    expect(result.current.isSelected('t1')).toBe(true);
  });

  it('leaves the others alone', () => {
    const { result } = renderHook(() => useThreadSelection(page, 3));
    act(() => result.current.toggle('t1'));
    expect(result.current.isSelected('t2')).toBe(false);
  });

  it('unpicks on a second press', () => {
    const { result } = renderHook(() => useThreadSelection(page, 3));
    act(() => result.current.toggle('t1'));
    act(() => result.current.toggle('t1'));
    expect(result.current.summary).toBe('Nothing selected');
  });

  it('selects everything, including what this list has not loaded', () => {
    const { result } = renderHook(() => useThreadSelection(page, 40));
    act(() => result.current.selectAll());
    expect(result.current.summary).toBe('All 40 selected');
  });

  it('says plainly that a select-all reaches past the visible list', () => {
    const { result } = renderHook(() => useThreadSelection(page, 40));
    act(() => result.current.selectAll());
    expect(result.current.beyondThisPage).toBe(true);
  });

  it('lets one be dropped from a select-all', () => {
    const { result } = renderHook(() => useThreadSelection(page, 40));
    act(() => result.current.selectAll());
    act(() => result.current.toggle('t1'));
    expect(result.current.summary).toBe('39 of 40 selected');
  });

  it('clears back to nothing', () => {
    const { result } = renderHook(() => useThreadSelection(page, 40));
    act(() => result.current.selectAll());
    act(() => result.current.clear());
    expect(result.current.count).toBe(0);
  });

  it('reports what is picked so it can be acted on', () => {
    const { result } = renderHook(() => useThreadSelection(page, 3));
    act(() => result.current.toggle('t2'));
    expect(result.current.pickedOnPage()).toEqual(['t2']);
  });

  it('reaches conversations the list has never loaded', () => {
    const { result } = renderHook(() => useThreadSelection(page, 40));
    act(() => result.current.selectAll());
    expect(result.current.targets(['t1', 't2', 't3', 't40'])).toEqual([
      't1',
      't2',
      't3',
      't40',
    ]);
  });

  it('leaves out what was dropped from a select-all', () => {
    const { result } = renderHook(() => useThreadSelection(page, 40));
    act(() => result.current.selectAll());
    act(() => result.current.toggle('t2'));
    expect(result.current.targets(['t1', 't2', 't3', 't40'])).toEqual(['t1', 't3', 't40']);
  });

  it('reaches only what was picked when picking one by one', () => {
    const { result } = renderHook(() => useThreadSelection(page, 40));
    act(() => result.current.toggle('t2'));
    expect(result.current.targets(['t1', 't2', 't3', 't40'])).toEqual(['t2']);
  });

  it('reaches nothing when nothing is picked', () => {
    const { result } = renderHook(() => useThreadSelection(page, 40));
    expect(result.current.targets(['t1', 't2'])).toEqual([]);
  });

  it('reports every visible row under a select-all', () => {
    const { result } = renderHook(() => useThreadSelection(page, 40));
    act(() => result.current.selectAll());
    expect(result.current.pickedOnPage()).toEqual(page);
  });
});
