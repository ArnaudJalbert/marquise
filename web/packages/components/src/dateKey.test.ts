import { describe, expect, it } from 'vitest';
import { addDaysToDateKey, parseDateKey, toDateKey } from './dateKey';

describe('toDateKey', () => {
  it('formats a date as YYYY-MM-DD', () => {
    const date = new Date(2026, 6, 15);
    expect(toDateKey(date)).toBe('2026-07-15');
  });

  it('pads single-digit months and days', () => {
    const date = new Date(2026, 0, 5);
    expect(toDateKey(date)).toBe('2026-01-05');
  });
});

describe('parseDateKey', () => {
  it('parses a date key into a Date at midnight local time', () => {
    const date = parseDateKey('2026-07-15');
    expect(date.getFullYear()).toBe(2026);
    expect(date.getMonth()).toBe(6);
    expect(date.getDate()).toBe(15);
  });

  it('round-trips through toDateKey', () => {
    const original = new Date(2026, 11, 25);
    expect(parseDateKey(toDateKey(original)).getDate()).toBe(25);
  });
});

describe('addDaysToDateKey', () => {
  it('adds positive days', () => {
    expect(addDaysToDateKey('2026-07-15', 3)).toBe('2026-07-18');
  });

  it('handles month boundaries', () => {
    expect(addDaysToDateKey('2026-07-30', 5)).toBe('2026-08-04');
  });

  it('handles year boundaries', () => {
    expect(addDaysToDateKey('2026-12-30', 5)).toBe('2027-01-04');
  });

  it('adds zero days', () => {
    expect(addDaysToDateKey('2026-07-15', 0)).toBe('2026-07-15');
  });

  it('subtracts days', () => {
    expect(addDaysToDateKey('2026-07-15', -5)).toBe('2026-07-10');
  });
});
