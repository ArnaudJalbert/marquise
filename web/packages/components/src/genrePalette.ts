import type { Genre } from './types';

export type PaletteFamily = 'sage' | 'clay' | 'seafoam' | 'sand' | 'sky';

/** Maps each genre to a companion-palette family used for tinted panels/labels (PW-03). */
export const GENRE_PALETTE: Record<Genre, PaletteFamily> = {
  Drama: 'sage',
  Comedy: 'clay',
  Documentary: 'seafoam',
  Family: 'sand',
  'Sci-Fi': 'sky',
  Musical: 'clay',
};
