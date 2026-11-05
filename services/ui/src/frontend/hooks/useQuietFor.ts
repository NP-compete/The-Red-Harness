import { useEffect, useState } from 'react';

/**
 * Seconds since `signature` last changed, counted only while `active`.
 * The signature is whatever stands for "something arrived".
 */
export function useQuietFor(active: boolean, signature: string): number {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    setSeconds(0);
    if (!active) return;
    const tick = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(tick);
  }, [active, signature]);

  return seconds;
}
