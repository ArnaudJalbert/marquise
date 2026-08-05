import { MovieGridController } from "marquise-components";

import { createMovieGridClient } from "./api-client";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";

// Module scope: the client is referentially stable so the grid controller
// never refetches on re-render. It only holds a best-effort cache, so the
// app never re-creates it.
const movieGridClient = createMovieGridClient();

export function App() {
  return (
    <div className="page-shell">
      <Header />
      <main className="site-main">
        <MovieGridController
          className="h-full w-full"
          client={movieGridClient}
          side="left"
          pageSize="auto"
          currentTime={new Date().toISOString()}
        />
      </main>
      <Footer />
    </div>
  );
}
