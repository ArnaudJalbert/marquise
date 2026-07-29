import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { PosterWallPage } from './PosterWallPage';
import { MovieDetailPage } from './MovieDetailPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PosterWallPage />} />
        <Route path="/movie/:movieId" element={<MovieDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App
