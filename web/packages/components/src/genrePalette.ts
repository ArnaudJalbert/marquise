export type PaletteFamily = 'sage' | 'clay' | 'seafoam' | 'sand' | 'sky';

/** Maps known genres to a companion-palette family used for tinted panels/labels (PW-03). */
export const GENRE_PALETTE: Record<string, PaletteFamily> = {
  Drama: 'sage',
  Comedy: 'clay',
  Documentary: 'seafoam',
  Family: 'sand',
  'Sci-Fi': 'sky',
  Musical: 'clay',
};

/** Resolve a palette family for any genre string, falling back to 'sage'. */
export function paletteFamily(genre: string): PaletteFamily {
  return GENRE_PALETTE[genre] ?? 'sage';
}
