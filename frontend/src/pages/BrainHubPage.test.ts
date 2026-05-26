import { describe, it, expect } from 'vitest';
import { topGroup } from './brainHubUtils';

describe('topGroup', () => {
  it('returns _orphan for undefined / empty group', () => {
    expect(topGroup(undefined)).toBe('_orphan');
    expect(topGroup('')).toBe('_orphan');
  });

  it('returns the exact bucket when the string matches a Johnny-Decimal prefix', () => {
    expect(topGroup('00_Core')).toBe('00_Core');
    expect(topGroup('03_Projects')).toBe('03_Projects');
    expect(topGroup('09_Archives')).toBe('09_Archives');
  });

  it('walks subfolders back up to their top-level bucket', () => {
    expect(topGroup('03_Projects/STL/widgets')).toBe('03_Projects');
    expect(topGroup('05_Resources/Research/2026')).toBe('05_Resources');
    expect(topGroup('08_Command-Center/Nexus9')).toBe('08_Command-Center');
  });

  it('returns _orphan for groups that do not match any prefix', () => {
    expect(topGroup('Random')).toBe('_orphan');
    expect(topGroup('99_Future')).toBe('_orphan');
  });
});
