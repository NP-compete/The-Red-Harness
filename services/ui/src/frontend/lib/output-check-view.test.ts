import { describe, expect, it } from 'vitest';

import { presentOutputCheck } from '@/lib/output-check-view';

const fits = {
  fits: true,
  missing: [] as string[],
  wrongShape: [] as string[],
  tooLong: [] as string[],
  unexpected: [] as string[],
  detail: '',
};

describe('presentOutputCheck', () => {
  it('shows nothing when the answer is the right shape', () => {
    expect(presentOutputCheck(fits)).toBeNull();
  });

  it('shows nothing for extra fields alone', () => {
    expect(presentOutputCheck({ ...fits, unexpected: ['invented'] })).toBeNull();
  });

  it('says plainly when something was left out', () => {
    const short = { ...fits, fits: false, missing: ['summary'], detail: 'missing: summary' };
    expect(presentOutputCheck(short)?.headline).toBe('The answer is missing summary');
  });

  it('names several missing parts', () => {
    const short = { ...fits, fits: false, missing: ['summary', 'risks'], detail: 'x' };
    expect(presentOutputCheck(short)?.headline).toBe('The answer is missing summary and risks');
  });

  it('says plainly when a part is the wrong shape', () => {
    const odd = { ...fits, fits: false, wrongShape: ['risks'], detail: 'x' };
    expect(presentOutputCheck(odd)?.headline).toBe('risks is not in the form that was asked for');
  });

  it('says plainly when a part runs long', () => {
    const wordy = { ...fits, fits: false, tooLong: ['summary'], detail: 'x' };
    expect(presentOutputCheck(wordy)?.headline).toBe('summary is longer than asked for');
  });

  it('leads with what is missing when several things are wrong', () => {
    const bad = { ...fits, fits: false, missing: ['summary'], wrongShape: ['risks'], detail: 'x' };
    expect(presentOutputCheck(bad)?.headline).toBe('The answer is missing summary');
  });

  it('carries the full detail for anyone who wants it', () => {
    const bad = {
      ...fits,
      fits: false,
      missing: ['summary'],
      wrongShape: ['risks'],
      detail: 'missing: summary; wrong shape: risks',
    };
    expect(presentOutputCheck(bad)?.detail).toBe('missing: summary; wrong shape: risks');
  });

  it('offers to ask again for a missing part', () => {
    const short = { ...fits, fits: false, missing: ['summary'], detail: 'x' };
    expect(presentOutputCheck(short)?.action).toBe('ask-again');
  });

  it('offers to shorten rather than re-ask when only length is wrong', () => {
    const wordy = { ...fits, fits: false, tooLong: ['summary'], detail: 'x' };
    expect(presentOutputCheck(wordy)?.action).toBe('shorten');
  });

  it('treats a missing part as serious', () => {
    const short = { ...fits, fits: false, missing: ['summary'], detail: 'x' };
    expect(presentOutputCheck(short)?.severity).toBe('high');
  });

  it('treats an overlong part as a nudge', () => {
    const wordy = { ...fits, fits: false, tooLong: ['summary'], detail: 'x' };
    expect(presentOutputCheck(wordy)?.severity).toBe('low');
  });

  it('mentions extra fields alongside a real problem', () => {
    const bad = { ...fits, fits: false, missing: ['summary'], unexpected: ['invented'], detail: 'x' };
    expect(presentOutputCheck(bad)?.note).toBe('It also included invented, which was not asked for');
  });

  it('has no such note when nothing extra was included', () => {
    const short = { ...fits, fits: false, missing: ['summary'], detail: 'x' };
    expect(presentOutputCheck(short)?.note).toBe('');
  });
});
