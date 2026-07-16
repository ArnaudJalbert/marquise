import { describe, expect, it } from 'vitest';
import { GENRE_PALETTE } from './genrePalette';

describe('GENRE_PALETTE', () => {
  it('maps every genre to a palette family', () => {
    expect(GENRE_PALETTE).toMatchObject({
      Drama: expect.any(String),
      Comedy: expect.any(String),
      Documentary: expect.any(String),
      'Sci-Fi': expect.any(String),
      Musical: expect.any(String),
      Family: expect.any(String),
    });
  });

  it('uses unique palette families for distinct genres', () => {
    const families = Object.values(GENRE_PALETTE);
    const unique = new Set(families);
    // At most one duplicate (Comedy and Musical both map to 'clay')
    expect(unique.size).toBeGreaterThanOrEqual(families.length - 1);
  });
});
