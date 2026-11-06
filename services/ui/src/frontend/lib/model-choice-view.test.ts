import { describe, expect, it } from 'vitest';

import { presentModelChoice } from '@/lib/model-choice-view';

const choice = {
  model: 'small',
  estimatedCost: 0.4,
  currency: 'USD',
  reason: '',
  refused: false,
  refusalReason: '',
};

describe('presentModelChoice', () => {
  it('names the model that will answer', () => {
    expect(presentModelChoice(choice).headline).toBe('Using small');
  });

  it('shows the estimated cost in money', () => {
    expect(presentModelChoice(choice).cost).toBe('about $0.40');
  });

  it('shows a very small cost without rounding it to nothing', () => {
    expect(presentModelChoice({ ...choice, estimatedCost: 0.004 }).cost).toBe('under $0.01');
  });

  it('says nothing extra for a routine choice', () => {
    expect(presentModelChoice(choice).detail).toBe('');
  });

  it('explains why a more capable model was needed', () => {
    const upgraded = { ...choice, model: 'large', reason: 'this request needs images and tools' };
    expect(presentModelChoice(upgraded).detail).toBe('this request needs images and tools');
  });

  it('says plainly when no model can do the job', () => {
    const refused = {
      ...choice,
      model: '',
      refused: true,
      refusalReason: 'no model can hold 500000 tokens with the features needed',
    };
    expect(presentModelChoice(refused).headline).toBe('This request cannot be run');
  });

  it('gives the reason nothing fits', () => {
    const refused = { ...choice, model: '', refused: true, refusalReason: 'too long' };
    expect(presentModelChoice(refused).detail).toBe('too long');
  });

  it('shows no cost for a request that cannot run', () => {
    const refused = { ...choice, model: '', refused: true, refusalReason: 'too long' };
    expect(presentModelChoice(refused).cost).toBe('');
  });

  it('suggests shortening when the request is too long', () => {
    const refused = {
      ...choice,
      model: '',
      refused: true,
      refusalReason: 'no model can hold 500000 tokens with the features needed',
    };
    expect(presentModelChoice(refused).action).toBe('shorten');
  });

  it('offers nothing to act on for a routine choice', () => {
    expect(presentModelChoice(choice).action).toBe('none');
  });

  it('treats a refusal as serious', () => {
    const refused = { ...choice, model: '', refused: true, refusalReason: 'x' };
    expect(presentModelChoice(refused).severity).toBe('high');
  });

  it('treats a routine choice as unremarkable', () => {
    expect(presentModelChoice(choice).severity).toBe('none');
  });

  it('formats cost in another currency', () => {
    expect(presentModelChoice({ ...choice, currency: 'EUR' }).cost).toBe('about €0.40');
  });
});
