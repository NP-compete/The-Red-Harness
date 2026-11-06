/**
 * A cron expression, said the way a person would say it.
 *
 * `0 8 * * 1-5` is how the scheduler stores it and not how anybody
 * reads it. The agent writes these from somebody's English, so the
 * screen owing them plain English back is the least it can do.
 *
 * **Anything it cannot phrase, it hands back unchanged.** A wrong
 * description of when a task runs is worse than a cron expression:
 * the expression at least looks like something to go and check,
 * while "every day at 08:00" for a schedule that does nothing of the
 * sort is a quiet lie. So the shapes below are the ones the agent
 * actually produces, each handled deliberately, and the rest fall
 * through.
 */

const DAYS = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
];

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

function timeOfDay(minute: string, hour: string): string | null {
  if (!/^\d{1,2}$/.test(minute) || !/^\d{1,2}$/.test(hour)) return null;
  const m = Number(minute);
  const h = Number(hour);
  if (m > 59 || h > 23) return null;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function listOfDays(field: string): string | null {
  // `1-5` is the weekday shorthand everyone writes, and the one the
  // agent reaches for; it is worth its own sentence rather than
  // "Monday, Tuesday, Wednesday, Thursday and Friday".
  if (field === '1-5') return 'every weekday';
  if (field === '0,6' || field === '6,0' || field === '0,6,' || field === '6-7')
    return 'every weekend day';

  const parts = field.split(',');
  const names: string[] = [];
  for (const part of parts) {
    if (!/^\d$/.test(part)) return null;
    const n = Number(part);
    if (n > 7) return null;
    names.push(DAYS[n === 7 ? 0 : n]);
  }
  if (names.length === 0) return null;
  if (names.length === 1) return `every ${names[0]}`;
  const last = names.pop() as string;
  return `every ${names.join(', ')} and ${last}`;
}

function ordinal(n: number): string {
  const rem100 = n % 100;
  if (rem100 >= 11 && rem100 <= 13) return `${n}th`;
  switch (n % 10) {
    case 1:
      return `${n}st`;
    case 2:
      return `${n}nd`;
    case 3:
      return `${n}rd`;
    default:
      return `${n}th`;
  }
}

/**
 * Describe a five-field cron expression, or return it unchanged.
 *
 * The returned string never starts with a capital, so a caller can
 * put it mid-sentence; capitalise at the point of use.
 */
export function cronInWords(expression: string): string {
  const fields = expression.trim().split(/\s+/);
  // Six fields is a seconds-first cron. This product has them off by
  // default and nothing here generates one, so rather than guess at
  // which end the extra field is, hand it back.
  if (fields.length !== 5) return expression;

  const [minute, hour, dayOfMonth, month, dayOfWeek] = fields;

  // Every minute.
  if (
    minute === '*' &&
    hour === '*' &&
    dayOfMonth === '*' &&
    month === '*' &&
    dayOfWeek === '*'
  ) {
    return 'every minute';
  }

  // Every N minutes.
  const everyNMinutes = /^\*\/(\d{1,2})$/.exec(minute);
  if (
    everyNMinutes &&
    hour === '*' &&
    dayOfMonth === '*' &&
    month === '*' &&
    dayOfWeek === '*'
  ) {
    const n = Number(everyNMinutes[1]);
    return n === 1 ? 'every minute' : `every ${n} minutes`;
  }

  // Every N hours, on the hour.
  const everyNHours = /^\*\/(\d{1,2})$/.exec(hour);
  if (
    everyNHours &&
    minute === '0' &&
    dayOfMonth === '*' &&
    month === '*' &&
    dayOfWeek === '*'
  ) {
    const n = Number(everyNHours[1]);
    return n === 1 ? 'every hour, on the hour' : `every ${n} hours`;
  }

  // Hourly at a given minute.
  if (hour === '*' && dayOfMonth === '*' && month === '*' && dayOfWeek === '*') {
    if (minute === '0') return 'every hour, on the hour';
    if (/^\d{1,2}$/.test(minute) && Number(minute) <= 59) {
      return `every hour at ${minute} minutes past`;
    }
    return expression;
  }

  const at = timeOfDay(minute, hour);
  if (at === null) return expression;

  // A day of the month, every month.
  if (dayOfMonth !== '*' && dayOfWeek === '*' && month === '*') {
    if (!/^\d{1,2}$/.test(dayOfMonth)) return expression;
    const d = Number(dayOfMonth);
    if (d < 1 || d > 31) return expression;
    return `on the ${ordinal(d)} of every month at ${at}`;
  }

  // A month and a day: once a year.
  if (dayOfMonth !== '*' && month !== '*' && dayOfWeek === '*') {
    if (!/^\d{1,2}$/.test(dayOfMonth) || !/^\d{1,2}$/.test(month)) return expression;
    const d = Number(dayOfMonth);
    const mo = Number(month);
    if (d < 1 || d > 31 || mo < 1 || mo > 12) return expression;
    return `every ${ordinal(d)} of ${MONTHS[mo - 1]} at ${at}`;
  }

  // Days of the week.
  if (dayOfMonth === '*' && month === '*') {
    if (dayOfWeek === '*') return `every day at ${at}`;
    const days = listOfDays(dayOfWeek);
    if (days === null) return expression;
    return `${days} at ${at}`;
  }

  return expression;
}

/**
 * When the next run falls, relative to now where that is clearer.
 *
 * "tomorrow at 08:00" is what somebody wants to know; the date is
 * kept for anything further out, because "in 23 days" is a number
 * nobody can plan around.
 */
export function nextRunInWords(iso: string | null, now: Date): string {
  if (!iso) return '';
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return iso;

  const at = `${String(when.getUTCHours()).padStart(2, '0')}:${String(
    when.getUTCMinutes()
  ).padStart(2, '0')}`;

  const startOfDay = (d: Date) =>
    Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  const days = Math.round(
    (startOfDay(when) - startOfDay(now)) / (24 * 60 * 60 * 1000)
  );

  if (days < 0) return `${at} UTC`;
  if (days === 0) return `today at ${at} UTC`;
  if (days === 1) return `tomorrow at ${at} UTC`;
  if (days < 7) return `${DAYS[when.getUTCDay()]} at ${at} UTC`;
  return `${when.getUTCDate()} ${MONTHS[when.getUTCMonth()]} at ${at} UTC`;
}
