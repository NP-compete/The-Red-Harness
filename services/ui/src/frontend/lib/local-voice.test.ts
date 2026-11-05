import { describe, expect, it } from 'vitest';

import { pickLocalVoice } from './local-voice';

const voice = (name: string, lang: string, localService: boolean) =>
  ({ name, lang, localService }) as SpeechSynthesisVoice;

describe('pickLocalVoice', () => {
  it('takes a voice that speaks the reader’s language', () => {
    const fr = voice('Amélie', 'fr-FR', true);
    expect(pickLocalVoice([voice('Alex', 'en-US', true), fr], 'fr')).toBe(fr);
  });

  it('matches a regional tag against a bare language', () => {
    const enGb = voice('Daniel', 'en-GB', true);
    expect(pickLocalVoice([enGb], 'en')).toBe(enGb);
  });

  it('prefers the exact tag over a sibling region', () => {
    const exact = voice('Daniel', 'en-GB', true);
    const sibling = voice('Alex', 'en-US', true);
    expect(pickLocalVoice([sibling, exact], 'en-GB')).toBe(exact);
  });

  it('refuses a voice that would send the words to a server', () => {
    // A remote voice posts the answer to whoever runs it. That is the
    // deployment's decision to make, not the browser's.
    expect(pickLocalVoice([voice('Cloud', 'en-US', false)], 'en')).toBeUndefined();
  });

  it('takes the local voice and leaves the remote one', () => {
    const local = voice('Alex', 'en-US', true);
    expect(pickLocalVoice([voice('Cloud', 'en-US', false), local], 'en')).toBe(local);
  });

  it('has no voice when none speaks the language', () => {
    expect(pickLocalVoice([voice('Alex', 'en-US', true)], 'ja')).toBeUndefined();
  });

  it('has no voice when the browser lists none', () => {
    expect(pickLocalVoice([], 'en')).toBeUndefined();
  });

  it('treats a voice that will not say whether it is local as remote', () => {
    const unsure = { name: 'Mystery', lang: 'en-US' } as SpeechSynthesisVoice;
    expect(pickLocalVoice([unsure], 'en')).toBeUndefined();
  });
});
