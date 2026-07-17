import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { PosterImage } from './PosterImage';

describe('PosterImage', () => {
  it('renders an img with the correct src and alt', () => {
    render(<PosterImage src="https://example.com/poster.jpg" alt="My Movie" />);
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', 'https://example.com/poster.jpg');
    expect(img).toHaveAttribute('alt', 'My Movie');
  });

  it('shows the placeholder on image error', () => {
    render(<PosterImage src="https://example.com/broken.jpg" alt="Broken" />);
    fireEvent.error(screen.getByRole('img'));
    const placeholder = screen.getByRole('img');
    expect(placeholder.tagName).toBe('DIV');
    expect(placeholder).toHaveAttribute('aria-label', 'Broken');
  });

  it('resets error state when src changes', () => {
    const { rerender } = render(<PosterImage src="https://example.com/first.jpg" alt="Test" />);
    fireEvent.error(screen.getByRole('img'));
    expect(screen.getByRole('img').tagName).toBe('DIV');

    rerender(<PosterImage src="https://example.com/second.jpg" alt="Test" />);
    expect(screen.getByRole('img').tagName).toBe('IMG');
    expect(screen.getByRole('img')).toHaveAttribute('src', 'https://example.com/second.jpg');
  });

  it('applies a custom className', () => {
    render(<PosterImage src="https://example.com/p.jpg" alt="A" className="custom-class" />);
    expect(screen.getByRole('img')).toHaveClass('custom-class');
  });
});
