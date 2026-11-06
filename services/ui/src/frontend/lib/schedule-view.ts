export interface ScheduleState {
  name: string;
  everySeconds: number;
  nextAt: string;
  paused: boolean;
  missed: number;
  lastOutcome: 'ok' | 'failed';
}

export interface PresentedSchedule {
  name: string;
  cadence: string;
  next: string;
  wouldResume: string;
  note: string;
  needsAttention: boolean;
  action: 'pause' | 'resume';
}

const HOUR = 3600;
const DAY = 86_400;

export function presentSchedule(schedule: ScheduleState, now: Date): PresentedSchedule {
  const until = describeUntil(new Date(schedule.nextAt).getTime() - now.getTime());

  return {
    name: schedule.name,
    cadence: describeCadence(schedule.everySeconds),
    next: schedule.paused ? 'paused' : until,
    // Shown even while paused, so resuming is not a leap in the dark.
    wouldResume: until,
    note:
      schedule.missed > 0
        ? `${schedule.missed} runs were missed. It will catch up once, not ${schedule.missed} times.`
        : '',
    needsAttention: schedule.lastOutcome === 'failed',
    action: schedule.paused ? 'resume' : 'pause',
  };
}

function describeCadence(seconds: number): string {
  if (seconds === DAY) return 'every day';
  if (seconds === HOUR) return 'every hour';
  if (seconds % DAY === 0) return `every ${seconds / DAY} days`;
  if (seconds % HOUR === 0) return `every ${seconds / HOUR} hours`;
  return `every ${Math.round(seconds / 60)} minutes`;
}

function describeUntil(ms: number): string {
  const hours = Math.round(ms / (HOUR * 1000));
  if (hours >= 24) {
    const days = Math.round(hours / 24);
    return `in ${days} day${days === 1 ? '' : 's'}`;
  }
  return `in ${hours} hour${hours === 1 ? '' : 's'}`;
}
