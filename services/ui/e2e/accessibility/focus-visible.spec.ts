/**
 * Everything you can reach by keyboard shows where you are.
 *
 * The contrast sweep next door cannot see this. Axe checks
 * colour, labels and structure on a page at rest; a focus ring
 * only exists while something is focused, and only for the one
 * element that is. So this walks the tab order and looks at each
 * stop in turn.
 *
 * What counts as visible: an outline with width, or — for
 * controls that suppress the outline deliberately — a box-shadow
 * standing in for one. A control with neither is reachable and
 * invisible, which is worse than one that cannot be reached at
 * all: the keyboard still goes there, and pressing Enter does
 * something the person did not see coming.
 *
 * The walk starts at the skip link and follows it, because the
 * sidebar is fifty conversations long and the panels behind it
 * are what these pages are for. That the skip link moves focus
 * at all is asserted here too — a skip link that scrolls without
 * moving focus looks right and helps nobody, and is the usual
 * way this breaks.
 */
import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

import { mountConfig } from '../helpers/config-mount';

interface Stop {
  tag: string;
  label: string;
  indicator: 'self' | 'none';
}

/**
 * Where focus is now, and whether you could tell by looking.
 *
 * Read while focus is genuinely there. A `.focus()` call from
 * script does not set `:focus-visible` — the browser reserves
 * that for focus it believes came from the keyboard — so a walk
 * that focuses programmatically reports no outline on controls
 * that plainly have one. This presses Tab and reads at the stop.
 *
 * Only the element's own styling is read. An earlier version
 * also walked up three ancestors, for controls that hand their
 * indicator to a container — the composer draws its ring on the
 * box around the textarea rather than the textarea itself. That
 * branch could not be made to fire against a planted example, so
 * it was removed rather than left in place looking like cover it
 * was not providing. The composer passes here on its own merits:
 * its border colour changes when focus arrives.
 *
 * The consequence to know: a control whose *only* indicator is
 * drawn by an ancestor would be reported as invisible. None
 * exists today. If one appears, the fix is to make this read the
 * ancestor too — and to prove it with an example that fails
 * without it.
 */
async function readFocused(page: Page): Promise<Stop | null> {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el || el === document.body) return null;

    const look = () => {
      const s = getComputedStyle(el);
      return [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.borderColor].join('|');
    };

    // While focus is really here, from a real Tab.
    const focused = look();
    // Then with focus gone, and back again so the next Tab
    // carries on from this element rather than from the top.
    el.blur();
    const resting = look();
    el.focus();

    const indicator: Stop['indicator'] = focused !== resting ? 'self' : 'none';

    return {
      tag: el.tagName.toLowerCase(),
      label: (
        el.getAttribute('aria-label') ||
        el.getAttribute('placeholder') ||
        el.textContent ||
        ''
      )
        .trim()
        .slice(0, 40),
      indicator,
    };
  });
}

/** Every distinct stop in the first `limit` presses of Tab. */
async function walk(page: Page, limit = 30): Promise<Stop[]> {
  const stops: Stop[] = [];
  const seen = new Set<string>();
  for (let i = 0; i < limit; i += 1) {
    await page.keyboard.press('Tab');
    const at = await readFocused(page);
    if (!at) continue;
    const key = `${at.tag}:${at.label}`;
    if (seen.has(key)) continue;
    seen.add(key);
    stops.push(at);
  }
  return stops;
}

/** Open a route and wait until it is actually interactive. */
async function open(page: Page, route: string) {
  await page.goto(route);
  // Tabbing into a page that has not rendered reaches nothing,
  // and a walk that reaches nothing passes for ever.
  await page.waitForSelector('#main-content', { state: 'attached' });
}

/** Where focus is now, for the skip-link checks. */
async function focusedLabel(page: Page) {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el || el === document.body) return null;
    return (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 40);
  });
}

const unseen = (stops: Stop[]) => stops.filter((s) => s.indicator === 'none');

const describeStops = (stops: Stop[]) =>
  stops.map((s) => `  ${s.tag} "${s.label}"`).join('\n');

test.describe('the skip link', () => {
  test.beforeEach(async ({ page }) => {
    await mountConfig(page);
  });

  test('is the first thing the keyboard reaches', async ({ page }) => {
    await open(page, '/settings');
    await page.keyboard.press('Tab');
    expect(await focusedLabel(page)).toMatch(/skip to main/i);
  });

  test('moves focus, not just the scroll position', async ({ page }) => {
    // The usual way this breaks: the target has no tabindex, so
    // the browser scrolls to it and leaves focus where it was.
    // The page looks right and the next Tab goes back into the
    // navigation the person was trying to escape.
    await open(page, '/settings');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    const landed = await page.evaluate(() => document.activeElement?.id);
    expect(landed).toBe('main-content');
  });

  test('lands before the panel, not back in the sidebar', async ({ page }) => {
    await open(page, '/settings');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    await page.keyboard.press('Tab');
    expect(await focusedLabel(page)).not.toMatch(/toggle sidebar|start new chat|search chat/i);
  });
});

test.describe('every stop in the tab order shows itself', () => {
  test.beforeEach(async ({ page }) => {
    await mountConfig(page);
  });

  for (const route of ['/', '/settings']) {
    test(`${route} — nothing is reachable and invisible`, async ({ page }) => {
      await open(page, route);
      const stops = await walk(page);

      // A walk that reaches nothing passes for ever.
      expect(stops.length, 'the walk reached nothing').toBeGreaterThanOrEqual(10);

      expect(
        unseen(stops),
        `Reachable with no focus indicator — the keyboard goes there and ` +
          `nothing says so:\n${describeStops(unseen(stops))}`,
      ).toEqual([]);
    });
  }
});

test.describe('the check can fail', () => {
  test.beforeEach(async ({ page }) => {
    await mountConfig(page);
  });

  test('a control with its outline removed is caught', async ({ page }) => {
    // Everything above passes today. What says the walk works is
    // a control that should fail and does — otherwise a check
    // that quietly matches nothing is indistinguishable from an
    // interface with no problems.
    await open(page, '/settings');
    await page.addStyleTag({
      content: 'button, a, input { outline: none !important; box-shadow: none !important; }',
    });
    const stops = await walk(page, 12);
    expect(stops.length).toBeGreaterThan(0);
    expect(unseen(stops).length).toBeGreaterThan(0);
  });
});
