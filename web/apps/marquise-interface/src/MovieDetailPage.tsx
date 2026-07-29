import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { MovieDetailPage as PageComponent } from '@marquise/components';
import { fetchMovieInfo, fetchMovieScreenings, fetchMovieDates } from './api';

export function MovieDetailPage() {
  const { movieId } = useParams<{ movieId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialDate = searchParams.get('date') ?? undefined;

  return (
    <PageComponent
      movieId={movieId ?? ''}
      initialDate={initialDate}
      onBack={() => navigate('/')}
      fetchMovieInfo={fetchMovieInfo}
      fetchMovieScreenings={fetchMovieScreenings}
      fetchMovieDates={fetchMovieDates}
    />
  );
}
