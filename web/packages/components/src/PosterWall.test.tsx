import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PosterWall } from './PosterWall';
import type { PosterMovie } from './types';

const sampleMovie: PosterMovie = {
  id: 'test-1',
  title: 'Test Movie',
  director: 'Test Director',
  year: 2026,
  runtimeMin: 120,
  format: 'DCP',
  genre: 'Drama',
  cinema: 'Test Cinema',
  dates: ['2026-07-15'],
  screenings: [{ time: '7:00 PM', lang: 'VO' }],
  poster: 'https://example.com/poster.jpg',
};

describe('PosterWall', () => {
  it('shows the empty state when no movies match', () => {
    render(<PosterWall view="PW-01" movies={[]} />);
    expect(screen.getByText('No screenings match these filters.')).toBeDefined();
  });

  it('renders PW-01 caption grid', () => {
    const { container } = render(<PosterWall view="PW-01" movies={[sampleMovie]} />);
    expect(container.querySelector('.poster-caption-grid')).toBeTruthy();
  });

  it('renders PW-02 dense grid', () => {
    const { container } = render(<PosterWall view="PW-02" movies={[sampleMovie]} />);
    expect(container.querySelector('.poster-dense-grid')).toBeTruthy();
  });

  it('renders PW-03 editorial grid', () => {
    const { container } = render(<PosterWall view="PW-03" movies={[sampleMovie]} />);
    expect(container.querySelector('.poster-editorial-grid')).toBeTruthy();
  });

  it('renders PW-04 listing grid', () => {
    const { container } = render(<PosterWall view="PW-04" movies={[sampleMovie]} />);
    expect(container.querySelector('.poster-listing-grid')).toBeTruthy();
  });
});
