import { describe, expect, it } from 'vitest';

import { presentResult } from '@/lib/subagent-result-view';

const result = {
  child: 'researcher',
  verdict: 'accepted' as const,
  answer: 'The limit is 500.',
  sources: ['handbook'],
  cost: '0.40',
  trusted: true,
  worthRetrying: false,
  reason: '',
};

describe('presentResult', () => {
  it('names the subagent that answered', () => {
    expect(presentResult(result).headline).toBe('researcher answered');
  });

  it('shows the answer', () => {
    expect(presentResult(result).answer).toBe('The limit is 500.');
  });

  it('lists what the answer rests on', () => {
    expect(presentResult(result).sources).toEqual(['handbook']);
  });

  it('says what the work cost', () => {
    expect(presentResult(result).cost).toBe('$0.40');
  });

  it('is quiet about an ordinary answer', () => {
    expect(presentResult(result).note).toBe('');
  });

  it('treats an ordinary answer as routine', () => {
    expect(presentResult(result).severity).toBe('info');
  });

  it('warns when nothing backs the answer', () => {
    const loose = { ...result, verdict: 'unsourced' as const, sources: [], reason: 'x' };
    expect(presentResult(loose).note).toBe('This answer cites nothing');
  });

  it('still shows an unsourced answer', () => {
    const loose = { ...result, verdict: 'unsourced' as const, sources: [], reason: 'x' };
    expect(presentResult(loose).answer).toBe('The limit is 500.');
  });

  it('treats an unsourced answer as worth a second look', () => {
    const loose = { ...result, verdict: 'unsourced' as const, sources: [], reason: 'x' };
    expect(presentResult(loose).severity).toBe('low');
  });

  it('says plainly when the subagent failed', () => {
    const broken = {
      ...result,
      verdict: 'failed' as const,
      answer: '',
      sources: [],
      worthRetrying: true,
      reason: 'the search tool was unavailable',
    };
    expect(presentResult(broken).headline).toBe('researcher could not finish');
  });

  it('gives the reason it failed', () => {
    const broken = {
      ...result,
      verdict: 'failed' as const,
      answer: '',
      sources: [],
      worthRetrying: true,
      reason: 'the search tool was unavailable',
    };
    expect(presentResult(broken).note).toBe('the search tool was unavailable');
  });

  it('still reports what a failure cost', () => {
    const broken = {
      ...result,
      verdict: 'failed' as const,
      answer: '',
      sources: [],
      cost: '0.20',
      worthRetrying: true,
      reason: 'x',
    };
    expect(presentResult(broken).cost).toBe('$0.20');
  });

  it('offers to ask again when that might help', () => {
    const broken = {
      ...result,
      verdict: 'failed' as const,
      answer: '',
      sources: [],
      worthRetrying: true,
      reason: 'x',
    };
    expect(presentResult(broken).retry).toBe(true);
  });

  it('does not offer to ask again for an answer already given', () => {
    expect(presentResult(result).retry).toBe(false);
  });

  it('says when the subagent came back with nothing', () => {
    const empty = {
      ...result,
      verdict: 'empty' as const,
      answer: '',
      sources: [],
      worthRetrying: true,
      reason: 'the subagent returned nothing',
    };
    expect(presentResult(empty).headline).toBe('researcher returned nothing');
  });

  it('marks work built on untrusted material', () => {
    expect(presentResult({ ...result, trusted: false }).quoted).toBe(true);
  });

  it('does not mark ordinary work', () => {
    expect(presentResult(result).quoted).toBe(false);
  });

  it('keeps an untrusted answer visible', () => {
    expect(presentResult({ ...result, trusted: false }).answer).toBe('The limit is 500.');
  });

  it('treats untrusted work as worth noticing even when accepted', () => {
    expect(presentResult({ ...result, trusted: false }).severity).toBe('medium');
  });

  it('treats a failure as worth noticing', () => {
    const broken = {
      ...result,
      verdict: 'failed' as const,
      answer: '',
      sources: [],
      worthRetrying: true,
      reason: 'x',
    };
    expect(presentResult(broken).severity).toBe('medium');
  });
});
