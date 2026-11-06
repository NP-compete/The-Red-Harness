import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { pickLocalVoice } from '../lib/local-voice';
import { speakable } from '../lib/speakable';

/** The voices this machine has, which a browser may list late. */
function useVoices(): SpeechSynthesisVoice[] {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    if (typeof speechSynthesis === 'undefined') return;
    const synth = speechSynthesis;
    const read = () => setVoices(synth.getVoices());
    read();
    synth.addEventListener('voiceschanged', read);
    return () => synth.removeEventListener('voiceschanged', read);
  }, []);

  return voices;
}

/**
 * Reading an answer out loud.
 *
 * Long answers are hard to take in by eye, and some readers cannot
 * take them in that way at all. The machine already has a voice, so
 * the only things needed here are to hand it prose instead of
 * markdown, to keep the words off the network, and to stop the moment
 * the reader leaves.
 */
export function useReadAloud(markdown: string, lang: string) {
  const [speaking, setSpeaking] = useState(false);
  const started = useRef(false);
  const text = useMemo(() => speakable(markdown), [markdown]);
  const voices = useVoices();
  const voice = useMemo(() => pickLocalVoice(voices, lang), [voices, lang]);

  const available = Boolean(voice) && text.length > 0;

  const stop = useCallback(() => {
    if (!started.current) return;
    started.current = false;
    if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel();
    setSpeaking(false);
  }, []);

  const toggle = useCallback(() => {
    if (!voice || !text || typeof speechSynthesis === 'undefined') return;
    if (started.current) {
      stop();
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.voice = voice;
    utterance.onend = () => {
      started.current = false;
      setSpeaking(false);
    };
    utterance.onerror = () => {
      started.current = false;
      setSpeaking(false);
    };
    started.current = true;
    setSpeaking(true);
    speechSynthesis.speak(utterance);
  }, [lang, stop, text, voice]);

  useEffect(() => stop, [stop]);

  return { available, speaking, toggle };
}
