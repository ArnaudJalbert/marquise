import { useEffect, useState } from 'react';
import { ImageOff } from 'lucide-react';
import './PosterImage.css';

export interface PosterImageProps {
  src: string;
  alt: string;
  className?: string;
}

/**
 * Poster-rendering primitive shared by every grid variant. Falls back to the
 * design system's documented placeholder (flat --n-100 panel + glyph) when
 * the source image is missing or fails to load — never a fake illustrated
 * poster.
 */
export function PosterImage({ src, alt, className }: PosterImageProps) {
  const [errored, setErrored] = useState(false);

  useEffect(() => {
    setErrored(false);
  }, [src]);

  if (errored) {
    return (
      <div className={`poster-image poster-image--placeholder ${className ?? ''}`} role="img" aria-label={alt}>
        <ImageOff className="poster-image__glyph" aria-hidden="true" />
      </div>
    );
  }

  return (
    <img
      className={`poster-image ${className ?? ''}`}
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setErrored(true)}
    />
  );
}
