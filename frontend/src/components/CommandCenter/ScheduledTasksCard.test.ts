import { describe, it, expect } from 'vitest';
import { urgencyFor } from './scheduledTaskUtils';

describe('urgencyFor', () => {
  it('returns idle when delta is null (no upcoming job)', () => {
    expect(urgencyFor(null)).toBe('idle');
  });

  it('returns overdue when the next run is in the past', () => {
    expect(urgencyFor(-1)).toBe('overdue');
    expect(urgencyFor(-3600_000)).toBe('overdue');
  });

  it('returns alert when next run is within 10 minutes', () => {
    expect(urgencyFor(1)).toBe('alert');
    expect(urgencyFor(5 * 60_000)).toBe('alert');
    expect(urgencyFor(10 * 60_000 - 1)).toBe('alert');
  });

  it('returns warn when next run is within the next hour but past 10 minutes', () => {
    expect(urgencyFor(10 * 60_000)).toBe('warn');
    expect(urgencyFor(30 * 60_000)).toBe('warn');
    expect(urgencyFor(60 * 60_000 - 1)).toBe('warn');
  });

  it('returns idle once the next run is more than an hour away', () => {
    expect(urgencyFor(60 * 60_000)).toBe('idle');
    expect(urgencyFor(24 * 60 * 60_000)).toBe('idle');
  });
});
