export function RequestState({
  loading,
  error,
  retry,
  subject = "screenings",
}: {
  loading: boolean;
  error?: unknown;
  retry: () => void;
  subject?: string;
}) {
  if (error)
    return (
      <div className="request-state" role="alert">
        <h2>The projector hit a snag.</h2>
        <p>We couldn't load the {subject}. Your plans are still salvageable.</p>
        <button onClick={retry}>Try again</button>
      </div>
    );
  if (loading)
    return (
      <div className="request-state" role="status">
        <p>Finding your next big-screen detour…</p>
        <div className="poster-skeletons">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} />
          ))}
        </div>
      </div>
    );
  return null;
}
export function Pagination({
  page,
  pages,
  total,
  onPage,
}: {
  page: number;
  pages: number;
  total: number;
  onPage: (page: number) => void;
}) {
  return (
    <nav className="screening-pagination" aria-label="Screening pages">
      <button disabled={page <= 1} onClick={() => onPage(page - 1)}>
        ← Previous
      </button>
      <span>
        Page {page} of {Math.max(1, pages)} · {total} screenings
      </span>
      <button disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Next →
      </button>
    </nav>
  );
}
