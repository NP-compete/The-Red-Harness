export interface SignedInDevice {
  fingerprint: string;
  label: string;
  lastSeen: string;
  trusted: boolean;
  current: boolean;
}

export interface DeviceRow {
  fingerprint: string;
  display: string;
  lastUsed: string;
  isThisOne: boolean;
  stale: boolean;
  note: string;
  action: 'sign-out' | 'none';
}

export interface PresentedDevices {
  rows: DeviceRow[];
  count: number;
  emptyMessage: string;
}

const STALE_DAYS = 90;
const DAY = 86_400_000;

export function presentDevices(devices: SignedInDevice[], now: Date): PresentedDevices {
  const rows = [...devices]
    .sort(
      (a, b) =>
        Number(b.current) - Number(a.current) || Date.parse(b.lastSeen) - Date.parse(a.lastSeen),
    )
    .map((device) => {
      const days = (now.getTime() - Date.parse(device.lastSeen)) / DAY;
      const stale = days > STALE_DAYS;

      return {
        fingerprint: device.fingerprint,
        // A fingerprint means nothing to a person and is not theirs to read.
        display: device.label || 'Unnamed device',
        lastUsed: device.current ? 'in use now' : ago(days),
        isThisOne: device.current,
        stale,
        note: stale ? 'Not used in a long time — remove it?' : '',
        action: device.current ? ('none' as const) : ('sign-out' as const),
      };
    });

  return {
    rows,
    count: rows.length,
    emptyMessage: rows.length <= 1 ? 'This is the only machine signed in' : '',
  };
}

function ago(days: number): string {
  const whole = Math.round(days);
  if (whole < 1) return 'today';
  return `${whole} day${whole === 1 ? '' : 's'} ago`;
}
