import { useCallback, useEffect, useRef, useState } from 'react';

import { dictationOffered, transcribeDictation } from '../services/speech-api';

const NO_MICROPHONE = 'No microphone is available, or permission for it was refused.';

// Long enough for someone to find the permission prompt and answer
// it; short enough that a request nobody will ever answer does not
// leave the control looking idle for ever.
const ANSWER_WITHIN_MS = 15000;

function timeBoxed<T>(work: Promise<T>): Promise<T> {
  return Promise.race([
    work,
    new Promise<T>((_resolve, reject) =>
      setTimeout(() => reject(new Error('no answer')), ANSWER_WITHIN_MS),
    ),
  ]);
}

/**
 * Speaking into the composer instead of typing it.
 *
 * The recording goes to the agent, which transcribes it where this
 * deployment already sends its content; nothing is sent on the
 * person's behalf. What comes back lands in the composer for them to
 * read, fix and send — a transcript is a guess, and sending one
 * unread is how the wrong thing gets asked.
 */
export function useDictation(onText?: (text: string) => void): {
  offered: boolean;
  recording: boolean;
  working: boolean;
  problem: string;
  start: () => Promise<void>;
  stop: () => void;
} {
  const [offered, setOffered] = useState(false);
  const [recording, setRecording] = useState(false);
  const [working, setWorking] = useState(false);
  const [problem, setProblem] = useState('');

  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const heard = useRef<Blob[]>([]);
  const deliver = useRef(onText);
  deliver.current = onText;

  useEffect(() => {
    let alive = true;
    const canRecord =
      typeof navigator !== 'undefined' &&
      !!navigator.mediaDevices?.getUserMedia &&
      typeof MediaRecorder !== 'undefined';
    if (!canRecord) return;
    void dictationOffered().then((yes) => {
      if (alive) setOffered(yes);
    });
    return () => {
      alive = false;
    };
  }, []);

  const release = useCallback(() => {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    recorder.current = null;
  }, []);

  const start = useCallback(async () => {
    setProblem('');
    // Asking can take as long as the person takes to answer, and a
    // control that looks idle while it waits reads as a dead button.
    setWorking(true);
    try {
      const got = await timeBoxed(navigator.mediaDevices.getUserMedia({ audio: true }));
      setWorking(false);
      stream.current = got;
      heard.current = [];

      const made = new MediaRecorder(got);
      made.ondataavailable = (event: BlobEvent) => {
        if (event.data?.size !== 0) heard.current.push(event.data);
      };
      made.onstop = () => {
        const recorded = new Blob(heard.current, { type: 'audio/webm' });
        release();
        setRecording(false);
        setWorking(true);
        void transcribeDictation(recorded).then((said) => {
          setWorking(false);
          if (said.problem) {
            setProblem(said.problem);
            return;
          }
          // Silence is an empty composer, not something to apologise
          // for; only text is worth handing on.
          if (said.text) deliver.current?.(said.text);
        });
      };

      recorder.current = made;
      made.start();
      setRecording(true);
    } catch {
      release();
      setWorking(false);
      setRecording(false);
      setProblem(NO_MICROPHONE);
    }
  }, [release]);

  const stop = useCallback(() => {
    recorder.current?.stop();
  }, []);

  useEffect(() => release, [release]);

  return { offered, recording, working, problem, start, stop };
}
