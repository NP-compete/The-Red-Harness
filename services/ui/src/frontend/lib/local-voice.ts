/**
 * A voice that speaks on this machine and nowhere else.
 *
 * Some of the voices a browser offers are services: the text is posted
 * to whoever runs them and the audio comes back. An answer may contain
 * anything the conversation contained, so sending it to a party the
 * deployment never named is not the browser's call to make. Only a
 * voice that says it is local is used, and where there is none, there
 * is no reading aloud.
 */
export function pickLocalVoice(
  voices: SpeechSynthesisVoice[],
  lang: string,
): SpeechSynthesisVoice | undefined {
  const local = voices.filter((voice) => voice.localService === true);
  const wanted = lang.toLowerCase();
  const base = wanted.split('-')[0];

  return (
    local.find((voice) => voice.lang.toLowerCase() === wanted) ??
    local.find((voice) => voice.lang.toLowerCase().split('-')[0] === base)
  );
}
