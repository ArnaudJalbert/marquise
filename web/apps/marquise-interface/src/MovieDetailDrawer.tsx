import { MovieDetailDrawer as DrawerComponent } from '@marquise/components';
import type { MovieDetailDrawerProps } from '@marquise/components';
import { fetchMovieScreenings, fetchMovieDates } from './api';

export type { MovieDetailDrawerProps };

export function MovieDetailDrawer(props: Omit<MovieDetailDrawerProps, 'fetchMovieScreenings' | 'fetchMovieDates'>) {
  return (
    <DrawerComponent
      {...props}
      fetchMovieScreenings={fetchMovieScreenings}
      fetchMovieDates={fetchMovieDates}
    />
  );
}
