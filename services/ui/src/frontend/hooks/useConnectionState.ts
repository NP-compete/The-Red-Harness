import { useEffect, useState } from 'react';

// Below this, an outage is a blip and saying so would be the interruption.
export const WARN_AFTER_SECONDS = 10;

export interface ConnectionReading {
  connected: boolean;
  secondsDown: number;
  warn: boolean;
}

export function useConnectionState(): ConnectionReading {
  const [connected, setConnected] = useState(() => navigator.onLine);
  const [secondsDown, setSecondsDown] = useState(0);

  useEffect(() => {
    const goOnline = () => {
      setConnected(true);
      setSecondsDown(0);
    };
    const goOffline = () => setConnected(false);

    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);

  useEffect(() => {
    if (connected) return;
    const tick = window.setInterval(() => setSecondsDown((s) => s + 1), 1000);
    return () => window.clearInterval(tick);
  }, [connected]);

  return {
    connected,
    secondsDown,
    warn: !connected && secondsDown >= WARN_AFTER_SECONDS,
  };
}
