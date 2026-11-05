import { describe, expect, it } from 'vitest';

import { presentBudget } from '@/lib/budget-view';

const spent = { withheld: ['grep'], scope: 'block' as const, limit: 3 };

describe('presentBudget', () => {
  it('says nothing when no tool was taken away', () => {
    expect(presentBudget(undefined)).toBeNull();
  });

  it('says nothing when the list of withheld tools is empty', () => {
    expect(presentBudget({ ...spent, withheld: [] })).toBeNull();
  });

  it('says plainly that the answer was written without a tool', () => {
    expect(presentBudget(spent)?.headline).toBe(
      'This answer was written without a tool',
    );
  });

  it('names the tool, because a count explains nothing', () => {
    expect(presentBudget(spent)?.detail).toContain('grep');
  });

  it('names the ceiling it went past', () => {
    expect(presentBudget(spent)?.detail).toContain('3 per block');
  });

  it('names a conversation ceiling as such', () => {
    const over = { withheld: ['grep'], scope: 'conversation' as const, limit: 5 };
    expect(presentBudget(over)?.detail).toContain('5 per conversation');
  });

  it('names every tool when more than one ran out', () => {
    const both = { ...spent, withheld: ['grep', 'execute_sql'] };
    expect(presentBudget(both)?.detail).toContain('execute_sql');
  });

  it('is told apart from a failure, because the answer still arrived', () => {
    expect(presentBudget(spent)?.failed).toBe(false);
  });
});
